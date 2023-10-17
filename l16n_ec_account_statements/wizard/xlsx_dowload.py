from odoo import models, fields


class Download(models.TransientModel):
    _name = 'download.xlsx'

    excel_file = fields.Binary('Descargar Reporte')
    file_name = fields.Char('File Name')