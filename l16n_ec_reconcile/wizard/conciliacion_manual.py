# -*- coding: utf-8 -*-
# © <2019> <Danner Marante Jacas>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models, _


class conciliacion_manual(models.TransientModel):
    _name = 'conciliacion.manual'
    move_id = fields.Integer('Movimiento')
    date = fields.Date('Fecha')


    def conciliar(self):
        id = int(self._context['move_id'])
        mov = self.env['account.move.line'].search([('id','=',id)])
        mov.conciled = True
        mov.conciled_date = self.date
