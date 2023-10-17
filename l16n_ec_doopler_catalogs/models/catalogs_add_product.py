from odoo import api, fields, models


# from ec_models import *


class AddCatalogInProduct(models.Model):
    _inherit = 'product.template'

    class_inherit = fields.Many2one('cproduct.doclass', 'Clase de producto')
    subclass_inherit = fields.Many2one('subproduct.dosubclass', 'Subclase de producto')
    fa_class_inherit = fields.Many2one('fproduct.dofamily', 'Familia de producto')
    mod_class_inherit = fields.Many2one('mproduct.domodel', 'Modelo de producto')
    sequence = fields.Integer("Secuencia", default=1)
    details_ok = fields.Boolean('Detalles', default=False)
    m2 = fields.Float(string='m2', compute='_compute_m2', store=True)

    @api.depends('anchorolloTela')
    def _compute_m2(self):
        for record in self:
            record.m2 = record.anchorolloTela * record.anchorolloTela

    #@api.onchange('class_inherit')
    #def _onchange_sclass(self):
        #for record in self.class_inherit:
        #    if record.cl_name:
        #        return {'domain': {'subclass_inherit': [('subclass_inherit','=',1)]}}
        #contador = 0

    # counter_se = fields.Char("contador s", default=lambda self: _('New'))
    # codes = fields.Char('Code', default=lambda self: _('New'), track_visibility='onchange')

    @api.model_create_multi
    def create(self, vals_list):
        producto = super(AddCatalogInProduct, self).create(vals_list)
        sequense = producto._calculate_sequence()
        code =self._generate_product_code(sequense)
        producto.write({'default_code': code, "sequence": sequense})
        return producto
    
    def write(self, vals):  
        vals['default_code'] = self._generate_product_code()
        producto = super(AddCatalogInProduct, self).write(vals)
        return producto
             
        
    @api.onchange('class_inherit')
    def change_class_inehrit(self):
        self.subclass_inherit = False
        self.fa_class_inherit = False
        self.mod_class_inherit = False
        self.default_code = self._generate_product_code()
    
    @api.onchange('subclass_inherit')
    def change_subclass_inherit(self):
        self.fa_class_inherit = False
        self.mod_class_inherit = False
        self.default_code = self._generate_product_code()
    
    @api.onchange('fa_class_inherit')
    def change_fa_class_inherit(self):
        
        self.mod_class_inherit = False
        self.default_code = self._generate_product_code()
    
    @api.onchange('mod_class_inherit')
    def change_mod_class_inherit(self):
        self.default_code = self._generate_product_code()
        
    def _generate_product_code(self,sequence = None):
        if sequence:
            str_seq = str(sequence).zfill(4)
        else:
            str_seq = str(self.sequence if self.sequence else 0).zfill(4)
        
        code = "{}-{}-{}-{}-{}".format(
            self.class_inherit.cl_name_code,
            self.subclass_inherit.scl_name_code,
            self.fa_class_inherit.f_name_code,
            self.mod_class_inherit.m_name_code,
            str_seq
        )
        return code
             

    def _calculate_sequence(self):
        self.ensure_one()
        sql = """
            select max("sequence")  from product_template pt 
        """
        self.env.cr.execute(sql)
        value = self.env.cr.fetchone()
        return value[0] + 1 if value[0] else 1
