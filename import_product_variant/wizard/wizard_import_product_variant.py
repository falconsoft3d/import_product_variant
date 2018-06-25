#-*- coding: utf-8 -*-

import os
import csv
import tempfile
from odoo.exceptions import UserError
from odoo import api, fields, models, _, SUPERUSER_ID


class ImportProductVariant(models.TransientModel):
    _name = "wizard.import.product.variant"

    file_data = fields.Binary('Archivo', required=True,)
    file_name = fields.Char('File Name')

    def import_button(self):
        if not self.csv_validator(self.file_name):
            raise UserError(_("El archivo debe ser de extension .csv"))
        file_path = tempfile.gettempdir()+'/file.csv'
        data = self.file_data
        f = open(file_path,'wb')
        f.write(data.decode('base64'))
        f.close() 
        archive = csv.DictReader(open(file_path))
        
        product_category_obj = self.env['product.category']
        attribute_obj = self.env['product.attribute']
        attribute_value_obj = self.env['product.attribute.value']
        product_obj = self.env['product.product']
        product_tmpl_obj = self.env['product.template']
        product_attr_line_obj = self.env['product.attribute.line']
        
        archive_lines = []
        for line in archive:
            archive_lines.append(line)
        
        columns = archive_lines[0].keys()
        # lista titulos de atributos de las columnas del csv ejemplo [v1:talla,v2:color]
        attributes_columns = []
        for col in columns:
            if self.check_attribute_column(col):
                attributes_columns.append(self.get_attribute_column(col))
        
        # lista de todo los atributos con variantes ejemplo [color:blanco,color:azul,talla:40]
        total_variants_attributes = []
        for attrib in attributes_columns:
            total_variants_attributes += self.get_variants_from_column(archive_lines,attrib)
        total_variants_attributes = list(set(total_variants_attributes))
        
        for attr_col in attributes_columns:
            attr = attr_col.split(':')[1].strip()
            attribute_id = attribute_obj.search([('name','=',attr)])
            if not attribute_obj.search([('name','=',attr)]):
                vals = {
                        'name': attr,
                        'create_variant': True,
                    }
                attribute_id = attribute_obj.create(vals)
            for variant in total_variants_attributes:
                cad = variant.split(':')
                value_id = attribute_value_obj.search([('name','=',cad[1])],limit=1)
                if not value_id:
                    if cad[0] ==  attr:
                        vals = {
                            'name': cad[1],
                            'attribute_id':attribute_id.id,
                        }
                        value_id = attribute_value_obj.create(vals)
                        
        products_names = [line.get('name',"") for line in archive_lines]
        products_names = list(set(products_names))
        cont=0
        for product_name in products_names:
            cont+=1
            product_tmpl_id = product_tmpl_obj.search([('name','=',product_name)])
            if not product_tmpl_id:
                vals = {
                    'name': product_name,
                }
                product_tmpl_id = product_tmpl_obj.create(vals)
                
                product_attributes = self.get_attributes(product_name, archive_lines, attributes_columns)
                product_variants_attributes = self.get_variants_attributes(product_name, archive_lines, attributes_columns)
                
                if product_attributes:
                    for attribute in product_attributes:
                        attribute_id = attribute_obj.search([('name','=',attribute)])
                        if attribute_id:
                            lis_variant = []
                            for product_variant in product_variants_attributes:
                                variant = product_variant.split(':')[1].strip()
                                if product_variant.split(':')[0].strip() == attribute:
                                    value_id = attribute_value_obj.search([('name','=',variant)],limit=1)
                                    if value_id:
                                        lis_variant.append(value_id.id)
                            if lis_variant:
                                vals = {
                                    'product_tmpl_id': product_tmpl_id.id,
                                    'attribute_id':attribute_id.id,
                                    'value_ids': [(6, 0, lis_variant)]
                                }
                                product_attribute_line_id = product_attr_line_obj.create(vals)
                                product_tmpl_id.create_variant_ids()
            else:
                if product_tmpl_id.attribute_line_ids:
                    
                    product_attributes = self.get_attributes(product_name, archive_lines, attributes_columns)
                    product_variants_attributes = self.get_variants_attributes(product_name, archive_lines, attributes_columns)
                    
                    lis_attr_tmpl = [str(line.attribute_id.name) for line in product_tmpl_id.attribute_line_ids]
                    lis_attr_tmpl = list(set(lis_attr_tmpl))
                    for attr in product_attributes:
                        attribute_id = attribute_obj.search([('name','=',attr)],limit=1)
                        if attr not in lis_attr_tmpl:
                            lis_variant = []
                            for product_variant in product_variants_attributes:
                                variant = product_variant.split(':')[1].strip()
                                if product_variant.split(':')[0].strip() == attr:
                                    value_id = attribute_value_obj.search([('name','=',variant)],limit=1)
                                    if value_id:
                                        lis_variant.append(value_id.id)
                            if attribute_id:
                                if lis_variant:
                                    vals = {
                                        'product_tmpl_id': product_tmpl_id.id,
                                        'attribute_id':attribute_id.id,
                                        'value_ids': [(6, 0, lis_variant)]
                                    }
                                    product_attribute_line_id = product_attr_line_obj.create(vals)
                                    product_tmpl_id.create_variant_ids()
                        else:
                            lis_attr_variant_tmpl = []
                            for line in product_tmpl_id.attribute_line_ids:
                                if line.attribute_id.name == attribute_id.name:
                                    for value_id in line.value_ids:
                                        lis_attr_variant_tmpl.append(str(value_id.name))
                            
                            lis_attr_variant_tmpl = list(set(lis_attr_variant_tmpl))
                            lis_attr_tmpl = [str(value_id.attribute_id.name) for value_id in product_tmpl_id.product_variant_id.attribute_value_ids]
                            lis_attr_tmpl = list(set(lis_attr_tmpl))
                   
                            if lis_attr_variant_tmpl:
                                lis_variant = []
                                for product_variant in product_variants_attributes:
                                    variant = product_variant.split(':')[1].strip()
                                    if product_variant.split(':')[0].strip() == attr:
                                        if variant not in lis_attr_variant_tmpl:
                                            value_id = attribute_value_obj.search([('name','=',variant)],limit=1)
                                            if value_id:
                                                lis_variant.append(value_id.id)
                                if attribute_id:
                                    if lis_variant:
                                        vals = {
                                            'product_tmpl_id': product_tmpl_id.id,
                                            'attribute_id':attribute_id.id,
                                            'value_ids': [(6, 0, lis_variant)]
                                        }
                                        product_attribute_line_id = product_attr_line_obj.create(vals)
                                        product_tmpl_id.create_variant_ids()
        
        for line in archive_lines:
            cont+=1
            name = line.get('name',"")
            default_code = line.get('code',"")
            
            product_ids = product_obj.search([('name','=',name)])
            product_template_id = product_tmpl_obj.search([('name','=',name)])
            
            list_attr_line = self.get_variants_attribute_line(line, attributes_columns)
            if list_attr_line:
                for product in product_ids:
                    list_attr = []
                    check = False
                    for values in product.attribute_value_ids:
                        list_attr.append(str(values.attribute_id.name)+':'+str(values.name))
                    if self.list_equal(list_attr_line, list_attr):
                        product.write({'default_code':default_code})
            else:
                product_template_id.write({'default_code':default_code})
        
        return {'type': 'ir.actions.act_window_close'}
        
    def list_equal(self, list_a, list_b):
        if len(list_a) != len(list_b):
            return False
        else:
            for i in range(0,len(list_a)):
                if list_a[i] not in list_b:
                    return False
        return True
        
    @api.model
    def get_attributes(self, product_name, archive_lines, attributes_columns):
        lis = []
        for line in archive_lines:
            if line.get('name',"") == product_name:
                for attr_col in attributes_columns:
                    if line.get(attr_col,"").strip() != "":
                        lis.append(attr_col.split(':')[1].strip())
        lis = list(set(lis))
        return lis
        
    @api.model
    def get_variants_attributes(self, product_name, archive_lines, attributes_columns):
        lis = []
        for line in archive_lines:
            if line.get('name',"") == product_name:
                for attr_col in attributes_columns:
                    if line.get(attr_col,"").strip() != "":
                        lis.append(attr_col.split(':')[1].strip()+':'+line.get(attr_col,"").strip())
        lis = list(set(lis))
        return lis
        
    @api.model
    def get_variants_attribute_line(self, line, attributes_columns):
        lis = []
        for att_col in attributes_columns:
            at = line.get(att_col,"")
            if at != "" and at != None and at != False and at != " ":
                lis.append(att_col.split(':')[1].strip()+":"+at)
        return lis
        
    @api.model
    def get_variants_from_column(self, archive_lines, attrib):
        lis_variant = [line.get(attrib,"") for line in archive_lines]
        lis_variant = list(set(lis_variant))
        for x in lis_variant[:]:
            if x == "" or x == None or x == False or x == " ":
                lis_variant.remove(x)
        lis = []
        for variant in lis_variant:
            lis.append(attrib.split(':')[1].strip()+':'+variant.strip())
        return lis
        
    @api.model
    def check_attribute_column(self,col):
        if col != "" and col != None and col != False and col != " " and col.count(':')>0:
            cad = col.split(':')
            if cad[0].count('v')>0 and cad[0].isalnum() or cad[0].count('variante')>0:
                if cad[1] != "" and cad[1] != None and cad[1] != False and cad[1] != " ":
                    return True
        return False    
            
    @api.model
    def get_attribute_column(self,col):
        if col != "" and col != None and col != False and col != " " and col.count(':')>0:
            cad = col.split(':')
            if cad[0].count('v')>0 and cad[0].isalnum() or cad[0].count('variante')>0:
                if cad[1] != "" and cad[1] != None and cad[1] != False and cad[1] != " ":
                    return col
        return False
        
    @api.model
    def csv_validator(self, xml_name):
        name, extension = os.path.splitext(xml_name)
        return True if extension == '.csv' else False
        
