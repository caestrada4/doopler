# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError



# class l16n_ec_doopler_catalogs(models.Model):
#     _name = 'l16n_ec_doopler_catalogs.l16n_ec_doopler_catalogs'
#     _description = 'l16n_ec_doopler_catalogs.l16n_ec_doopler_catalogs'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

class DoClassCatalog(models.Model):
    _name = 'cproduct.doclass'
    _description = 'Class Product Doopler'
    _rec_name = 'cl_name'

    c_id = fields.Many2one('cproduct.doclass')
    cl_name = fields.Char('Clases de productos', required=True)
    cl_name_code = fields.Char('Código de clase', required=True, size=4)
    _sql_constraints = [
        ('cl_name_code_uniq', 'unique (cl_name_code)', "Código ya registrado!"),
    ]

    #Relaciones entre tablas subclase
    scl_product_ids = fields.One2many('subproduct.dosubclass','cl_product_id', string='Subclases')

    @api.ondelete(at_uninstall=False)
    def check_del_class(self):
        for clpro in self:
            if clpro.scl_product_ids:
                raise ValidationError(_("No se puede eliminar debido que forma parte de otro catálogo o producto"))


class DoSubClassCatalog(models.Model):
    _name = 'subproduct.dosubclass'
    _description = 'Sub Class Product Doopler'
    _rec_name = 'scl_name'

    scl_name = fields.Char('Subclase de producto', required=True)
    scl_name_code = fields.Char('Código de subclase', required=True, size=4)

    #apunta a clase
    cl_product_id = fields.Many2one('cproduct.doclass', string="Clase")

    #Relacion entre tablas Family
    f_product_ids = fields.One2many('fproduct.dofamily','scl_product_id', string='Subclases')
    
    _sql_constraints = [
        ('scl_name_code_uniq', 'unique (scl_name_code)', "Código ya registrado!"),
    ]

    @api.ondelete(at_uninstall=False)
    def check_del_class(self):
        for sclpro in self:
            if sclpro.f_product_ids:
                raise ValidationError(_("No se puede eliminar debido que forma parte de otro catálogo o producto"))


class DoFamilyCatalog(models.Model):
    _name = 'fproduct.dofamily'
    _description = 'Family Product Doopler'
    _rec_name = 'f_name'

    f_name = fields.Char('Familia de producto', required=True)
    f_name_code = fields.Char('Código de familia', required=True, size=4)

    #Relacion entre tabla modelo
    #m_product_ids = fields.One2many('mproduct.domodel', 'm_product_id', string='Family')

    #apunta a subclase
    scl_product_id = fields.Many2one('subproduct.dosubclass', "Subclase")
    _sql_constraints = [
        ('f_name_code_uniq', 'unique (f_name_code)', "Código ya registrado!"),
    ]



class DoModelCatalog(models.Model):
    _name = 'mproduct.domodel'
    _description = 'Model Product Doopler'
    _rec_name = 'm_name'

    m_name = fields.Char('Modelo de producto', required=True)
    m_name_code = fields.Char('Código de Modelo', required=True, size=4, unique=True)

    #Apunta a Familia
    f_product_id = fields.Many2one('fproduct.dofamily', string="Familia")
    
    _sql_constraints = [
        ('f_mproduct_name_code_uniq', 'unique (m_name_code)', "Código ya registrado!"),
    ]







