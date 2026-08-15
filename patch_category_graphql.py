import re

with open("app/products/categories/graphql.py", "r") as f:
    content = f.read()

# Replace DBCategory with MongoCategory
content = content.replace(
    "from app.products.categories.models import Category as DBCategory",
    "from app.products.categories.mongo_models import Category as DBCategory\nfrom app.products.products.mongo_models import Product as DBProduct"
)

# Remove SQLAlchemy imports
content = re.sub(r"from sqlalchemy.future import select\n", "", content)

# Fix CategoryType parent
content = content.replace(
    "db_parent = await category_service.get_category_by_id(db, tenant_id, self.parent_id)",
    "db_parent = await category_service.get_category_by_id(tenant_id, self.parent_id)"
)

# Fix CategoryType children
children_replacement = """        tenant_id = info.context.tenant_id or self.tenant_id
        db_children = await DBCategory.find({"parent_id": self.id, "tenant_id": tenant_id}).sort("-created_at").to_list()
        return [CategoryType(c) for c in db_children]"""
content = re.sub(r"        db = info\.context\.db\n        from sqlalchemy\.future import select\n        stmt = select\(DBCategory\)\.where\([\s\S]*?db_children = res\.scalars\(\)\.all\(\)\n        return \[CategoryType\(c\) for c in db_children\]", children_replacement, content)

# Fix CategoryType products
products_replacement = """        tenant_id = info.context.tenant_id or self.tenant_id
        db_products = await DBProduct.find({"category_ids": self.id, "tenant_id": tenant_id}).sort("-created_at").to_list()
        from app.products.products.graphql import ProductType
        return [ProductType(p) for p in db_products]"""
content = re.sub(r"        db = info\.context\.db\n        from sqlalchemy\.future import select\n        from app\.products\.products\.models import Product as DBProduct\n        from app\.products\.categories\.models import ProductCategory\n        from app\.products\.products\.graphql import ProductType\n        stmt = select\(DBProduct\)[\s\S]*?db_products = res\.scalars\(\)\.all\(\)\n        return \[ProductType\(p\) for p in db_products\]", products_replacement, content)

# Remove db=db in services calls
content = content.replace("db=db,\n", "")
content = content.replace("db=db", "")
content = content.replace("await category_service.get_categories(db, tenant_id, search=search)", "await category_service.get_categories(tenant_id, search=search)")
content = content.replace("await category_service.get_category_by_id(db, tenant_id, id)", "await category_service.get_category_by_id(tenant_id, id)")
content = content.replace("await category_service.delete_category(\n            db,\n", "await category_service.delete_category(\n")
content = content.replace("await category_service.delete_category(\n            tenant_id=tenant_id", "await category_service.delete_category(\n            tenant_id=tenant_id")


with open("app/products/categories/graphql.py", "w") as f:
    f.write(content)
