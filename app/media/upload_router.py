import uuid
import httpx
import jwt
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.users.models import User
from app.database.postgres import get_db_session
from app.auth.services import auth_service
from app.users.services import user_service

router = APIRouter(prefix="/api/media", tags=["Media Upload"])

VERCEL_BLOB_URL = "https://blob.vercel-storage.com"

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header.")
    
    token = auth_header.split(" ")[1]
    try:
        payload = auth_service.decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type.")
            
        user_id_str = payload.get("sub")
        tenant_id_str = payload.get("tenant_id")
        
        if not user_id_str or not tenant_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing user or tenant ID.")
            
        user_id = uuid.UUID(user_id_str)
        tenant_id = uuid.UUID(tenant_id_str)
        
        user = await user_service.get_user_by_id(db, user_id, tenant_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token signature has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format or signature.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Authentication failed: {str(e)}")

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    entity_type: str = Form(..., description="e.g., product, category, logo"),
    entity_id: str = Form(None, description="The ID of the product or entity to use as the filename"),
    old_media_url: str = Form(None, description="Provide old URL to delete it from storage"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Unified endpoint to upload files to Vercel Blob.
    Generates a secure path like: {tenant_id}/{entity_type}/{filename}
    """
    if not settings.VERCEL_BLOB_READ_WRITE_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vercel Blob token is not configured on the server."
        )

    # Clean entity_type
    entity_type = entity_type.strip().lower()
    if not entity_type:
        entity_type = "general"

    # Ensure tenant_id exists
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant to upload files."
        )

    # Delete old media from Vercel and PostgreSQL if provided
    if old_media_url and settings.VERCEL_BLOB_READ_WRITE_TOKEN:
        async with httpx.AsyncClient() as client:
            # We don't block the upload if delete fails, we just try to clean up
            try:
                await client.post(
                    f"{VERCEL_BLOB_URL}/delete",
                    headers={"Authorization": f"Bearer {settings.VERCEL_BLOB_READ_WRITE_TOKEN}"},
                    json={"urls": [old_media_url]}
                )
                
                # Delete the old record from the database so the frontend doesn't show it anymore
                from sqlalchemy.future import select
                from app.media.models import Media
                stmt = select(Media).where(Media.media_url == old_media_url)
                res = await db.execute(stmt)
                old_media_record = res.scalar_one_or_none()
                if old_media_record:
                    await db.delete(old_media_record)
                    await db.commit()
            except Exception as e:
                print(f"Failed to delete old media: {str(e)}")

    # Ensure filename is completely unique and secure
    extension = ""
    if file.filename and "." in file.filename:
        extension = f".{file.filename.split('.')[-1]}"
    
    # Use entity_id if provided and valid, otherwise fallback to random UUID
    # We ignore 'undefined', 'null', and the tenant_id in case the frontend sends them by mistake for new products
    invalid_ids = ["undefined", "null", "", str(tenant_id)]
    if not entity_id or str(entity_id).lower().strip() in invalid_ids:
        base_name = str(uuid.uuid4())
    else:
        base_name = str(entity_id).replace(" ", "_")
        
    # Append a short timestamp to prevent browser and CDN caching issues!
    import time
    timestamp = int(time.time())
    safe_filename = f"{base_name}-{timestamp}{extension}"
    
    # Construct the blob path: {tenant_id}/{entity_type}/{safe_filename}
    blob_path = f"{tenant_id}/{entity_type}/{safe_filename}"

    # Prepare Vercel Blob REST Request
    headers = {
        "Authorization": f"Bearer {settings.VERCEL_BLOB_READ_WRITE_TOKEN}",
        "x-api-version": "7",
        "x-vercel-blob-access": "public"
    }
    
    file_bytes = await file.read()
    
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{VERCEL_BLOB_URL}/{blob_path}",
            headers=headers,
            content=file_bytes
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to upload to Vercel Blob. Status: {response.status_code}, Response: {response.text}"
            )
            
        data = response.json()
        url = data.get("url")
        
        # Create a database record for this media
        from app.media.services import media_service
        media_id = None
        try:
            valid_entity_id = None
            if entity_id and str(entity_id).lower().strip() not in invalid_ids:
                valid_entity_id = uuid.UUID(str(entity_id))
                
            db_media = await media_service.create_media(
                db=db,
                tenant_id=tenant_id,
                file_path=blob_path,
                media_url=url,
                media_type="IMAGE",
                file_extension=extension.replace(".", "") if extension else None,
                entity_name=entity_type,
                entity_id=valid_entity_id,
                user_id=current_user.id
            )
            media_id = str(db_media.id)
        except Exception as e:
            print(f"Failed to save media to DB: {str(e)}")
            
        print("====== UPLOAD SUCCESS ======")
        print("Vercel Blob returned data:", data)
        print("URL being sent to frontend:", url)
        print("DB Media ID:", media_id)
        print("============================")
        
        return {
            "id": media_id,
            "url": url,
            "path": blob_path,
            "filename": safe_filename,
            "entity_type": entity_type
        }

@router.post("/upload-multiple")
async def upload_multiple_files(
    files: list[UploadFile] = File(...),
    entity_type: str = Form(..., description="e.g., product, category, logo"),
    entity_id: str = Form(None, description="The ID of the product or entity to use as the filename"),
    old_media_urls: str = Form(None, description="Comma-separated list of old URLs to delete"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Endpoint to upload up to 5 files to Vercel Blob at once.
    """
    if len(files) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can upload a maximum of 5 images at once."
        )

    if not settings.VERCEL_BLOB_READ_WRITE_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vercel Blob token is not configured on the server."
        )

    entity_type = entity_type.strip().lower()
    if not entity_type:
        entity_type = "general"

    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant to upload files."
        )

    invalid_ids = ["undefined", "null", "", str(tenant_id)]

    # Delete old media from Vercel and PostgreSQL if provided
    if old_media_urls and settings.VERCEL_BLOB_READ_WRITE_TOKEN:
        urls_to_delete = [url.strip() for url in old_media_urls.split(",") if url.strip()]
        if urls_to_delete:
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(
                        f"{VERCEL_BLOB_URL}/delete",
                        headers={"Authorization": f"Bearer {settings.VERCEL_BLOB_READ_WRITE_TOKEN}"},
                        json={"urls": urls_to_delete}
                    )
                    
                    from sqlalchemy.future import select
                    from app.media.models import Media
                    stmt = select(Media).where(Media.media_url.in_(urls_to_delete))
                    res = await db.execute(stmt)
                    old_media_records = res.scalars().all()
                    for old_record in old_media_records:
                        await db.delete(old_record)
                    if old_media_records:
                        await db.commit()
                except Exception as e:
                    print(f"Failed to delete old media: {str(e)}")
    
    headers = {
        "Authorization": f"Bearer {settings.VERCEL_BLOB_READ_WRITE_TOKEN}",
        "x-api-version": "7",
        "x-vercel-blob-access": "public"
    }

    results = []
    
    from app.media.services import media_service

    async with httpx.AsyncClient() as client:
        for file in files:
            extension = ""
            if file.filename and "." in file.filename:
                extension = f".{file.filename.split('.')[-1]}"
            
            if not entity_id or str(entity_id).lower().strip() in invalid_ids:
                base_name = str(uuid.uuid4())
            else:
                base_name = str(entity_id).replace(" ", "_")
                
            import time
            timestamp = int(time.time() * 1000)
            safe_filename = f"{base_name}-{timestamp}{extension}"
            
            blob_path = f"{tenant_id}/{entity_type}/{safe_filename}"
            
            file_bytes = await file.read()
            
            response = await client.put(
                f"{VERCEL_BLOB_URL}/{blob_path}",
                headers=headers,
                content=file_bytes
            )
            
            if response.status_code != 200:
                results.append({"filename": file.filename, "error": f"Failed to upload. Status: {response.status_code}"})
                continue
                
            data = response.json()
            url = data.get("url")
            
            media_id = None
            try:
                valid_entity_id = None
                if entity_id and str(entity_id).lower().strip() not in invalid_ids:
                    valid_entity_id = uuid.UUID(str(entity_id))
                    
                db_media = await media_service.create_media(
                    db=db,
                    tenant_id=tenant_id,
                    file_path=blob_path,
                    media_url=url,
                    media_type="IMAGE",
                    file_extension=extension.replace(".", "") if extension else None,
                    entity_name=entity_type,
                    entity_id=valid_entity_id,
                    user_id=current_user.id
                )
                media_id = str(db_media.id)
            except Exception as e:
                print(f"Failed to save media to DB: {str(e)}")
                
            results.append({
                "id": media_id,
                "url": url,
                "path": blob_path,
                "filename": safe_filename,
                "entity_type": entity_type
            })

    return {"uploaded_files": results}
