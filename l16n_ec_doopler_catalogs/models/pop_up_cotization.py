from odoo import api, fields, models, _
from odoo.exceptions import (UserError)
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    dirEntrega=fields.Char(string="Direccion de entrega")
    
    def action_confirm(self):
        for line in self.order_line:
            if line.product_details_ok:
                if not line.details_id:
                    raise UserError(_('El producto %s requiere de detalles') % (line.product_id.name))
        sale = super(SaleOrder, self).action_confirm()
        
        return sale
            
             

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    product_details_ok = fields.Boolean(string='Product Details',related='product_template_id.details_ok')
    metros2=fields.Float(related='product_template_id.m2')
    details_id = fields.Many2one('sale.order.pop', string='Detalle del producto',required=False, ondelete='cascade')
    details_name = fields.Char(string='Descripción')
    def create_details(self):
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.pop',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'sale_order_line': self.id}, 
            'res_id': self.details_id.id,
            'id': self.details_id.id,
            }


    
