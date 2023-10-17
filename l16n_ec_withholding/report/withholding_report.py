# -*- coding: utf-8 -*-


from odoo import api, models
import logging

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MONTHS = {
    '01':'Enero',
    '02':'Febrero',
    '03':'Marzo',
    '04':'Abril',
    '05':'Mayo',
    '06':'Junio',
    '07':'Julio',
    '08':'Agosto',
    '09':'Septiembre',
    '10':'Octubre',
    '11':'Noviembre',
    '12':'Diciembre',
}

class ReporteRetencion(models.AbstractModel):
    _name = 'report.l16n_ec_withholding.withholding_report'


    @api.model
    def _get_report_values(self, docids, data=None):
        # try:
        # val = self.env['account.retention'].browse(docids)
        # docargs = {
        #     'doc_ids': docids,
        #     'doc_model': 'account.retention',
        #     'docs': val,
        # }
        a = 1
        return {
            'doc_ids': docids,
            'doc_model': self.env['account.retention'],
            'data': data,
            'docs': self.env['account.retention'].browse(docids)
        }

        # return self.env['report'].render('l16n_ec_withholding.withholding_report', values=docargs)  # noqa
        # except ValueError:
        #     raise UserError(u'No existe documento asociado.')


