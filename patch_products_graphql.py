import re

with open("app/products/products/graphql.py", "r") as f:
    content = f.read()

# Replace DBProduct with MongoProduct and fix models import
content = content.replace(
    "from app.products.products.models import (",
    "from app.products.products.mongo_models import (\n    Product as DBProduct,\n    Attribute as DBAttribute,\n    AttributeValueModel as DBAttributeValue,\n    ProductAttributeModel as DBProductAttributeValue,\n    ProductGroup as DBProductGroup,\n    ProductGroupLinkModel as DBProductGroupLink,\n    ProductStockModel as DBProductStock\n)\n# "
)

# Remove SQLAlchemy imports
content = re.sub(r"from sqlalchemy.future import select\n", "", content)

# Remove DataLoader references for embedded fields and replace with direct references.

# Fix ProductType attributes
attr_repl = """        return [ProductAttributeValueType(pav) for pav in self.attributes]"""
content = re.sub(r"        db = info\.context\.db\n        from sqlalchemy\.future import select\n        from app\.products\.products\.models import ProductAttributeValue\n        stmt = select\(ProductAttributeValue\)\.where\(ProductAttributeValue\.product_id == self\.id\)\n        res = await db\.execute\(stmt\)\n        db_pavs = res\.scalars\(\)\.all\(\)\n        return \[ProductAttributeValueType\(pav\) for pav in db_pavs\]", attr_repl, content)

# Fix ProductType groups
grp_repl = """        return [ProductGroupLinkType(link) for link in self.groups]"""
content = re.sub(r"        db = info\.context\.db\n        from sqlalchemy\.future import select\n        stmt = select\(DBProductGroupLink\)\.where\(DBProductGroupLink\.product_id == self\.id\)\n        res = await db\.execute\(stmt\)\n        db_links = res\.scalars\(\)\.all\(\)\n        return \[ProductGroupLinkType\(link\) for link in db_links\]", grp_repl, content)

# Fix ProductType stock
stk_repl = """        return self.stock.stock if self.stock else 0"""
content = re.sub(r"        if not info\.context\.dataloaders:\n            return 0\n        return await info\.context\.dataloaders\.stock_loader\.load\(self\.id\)", stk_repl, content)

# Fix effective_price
eff_stk_repl = """        stock = self.stock.stock if self.stock else 0"""
content = content.replace("        stock = await info.context.dataloaders.stock_loader.load(self.id)", eff_stk_repl)

# Fix ProductType categories dataloader to use category_loader which was fixed
cat_repl = """        if not info.context.dataloaders:
            return []
        db_categories = await info.context.dataloaders.category_loader.load_many(self.category_ids)
        from app.products.categories.graphql import CategoryType
        return [CategoryType(c) for c in db_categories if c]"""
content = re.sub(r"        if not info\.context\.dataloaders:\n            return \[\]\n        db_categories = await info\.context\.dataloaders\.category_loader\.load\(self\.id\)\n        from app\.products\.categories\.graphql import CategoryType\n        return \[CategoryType\(c\) for c in db_categories\]", cat_repl, content)

# Remove db=db in services calls
content = content.replace("db=db,\n", "")
content = content.replace("db=db", "")
content = content.replace("await product_service.get_product_by_id(db, tenant_id, self.parent_id)", "await product_service.get_product_by_id(tenant_id, self.parent_id)")
content = content.replace("await product_service.get_related_products(db, tenant_id, self.id)", "await product_service.get_related_products(tenant_id, self.id)")
content = content.replace("await product_service.get_products(db, tenant_id, product_type=pt_val, search=search)", "await product_service.get_products(tenant_id, product_type=pt_val, search=search)")
content = content.replace("await product_service.get_product_by_id(db, tenant_id, id)", "await product_service.get_product_by_id(tenant_id, id)")
content = content.replace("await product_service.get_attributes(db, tenant_id)", "await product_service.get_attributes(tenant_id)")
content = content.replace("await product_service.get_attribute_by_id(db, tenant_id, id)", "await product_service.get_attribute_by_id(tenant_id, id)")
content = content.replace("await product_service.get_attribute_values(db, tenant_id, attribute_id)", "await product_service.get_attribute_values(tenant_id, attribute_id)")
content = content.replace("await product_service.get_attribute_values(db, tenant_id, self.id)", "await product_service.get_attribute_values(tenant_id, self.id)")
content = content.replace("await product_service.get_product_groups(db, tenant_id)", "await product_service.get_product_groups(tenant_id)")
content = content.replace("await product_service.get_product_group_by_id(db, tenant_id, id)", "await product_service.get_product_group_by_id(tenant_id, id)")
content = content.replace("await product_service.get_product_group_by_id(db, tenant_id, self.group_id)", "await product_service.get_product_group_by_id(tenant_id, self.group_id)")


with open("app/products/products/graphql.py", "w") as f:
    f.write(content)
