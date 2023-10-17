import base64
import io

import xlwt
from datetime import datetime
from odoo import fields, models


class AccountStatementsWizard(models.Model):
    _name = 'account.statements.wizard'
    _description = 'Generate account statements'
    start_date = fields.Date('Fecha de Inicio')
    end_date = fields.Date('Fecha de fin', default=datetime.today())
    report_type = fields.Selection([('consolidate', 'Consolidado'), ('detailed', 'Detallado')],
                                   string="Typo de Reporte", default='consolidate')

    def _lines(self, report_type):
        domain = []
        domain.append(('state', 'not in', ['draft', 'cancel']))
        if report_type == 'out_invoice':
            domain.append(('move_type', '=', 'out_invoice'))
        else:
            domain.append(('move_type', '=', 'in_invoice'))
        if self.start_date:
            domain.append(('invoice_date', '>=', self.start_date))
        if self.end_date:
            domain.append(('invoice_date', '<=', self.end_date))

        invoices = self.env['account.move'].search(domain)
        lines_return = []
        for item in invoices:
            lines_return.append({
                'date': item.invoice_date.strftime('%Y-%m-%d'),
                'type': 'FC',
                'number': item.name,
                'name': item.partner_id.name,
                'debit': item.amount_total if report_type == 'in_invoice' else '0.0',
                'credit': item.amount_total if report_type == 'out_invoice' else '0.0',
                'amount_residual': item.amount_residual,
                'no_document': item.l10n_latam_document_number,
                'document_value': item.amount_total,
            })
            # invoice_payments_widget
            if item.invoice_payments_widget and self.report_type == 'detailed':
                for payment in item.invoice_payments_widget['content']:
                    lines_return.append({
                        'date': payment['date'].strftime('%Y-%m-%d'),
                        'type': 'TR',
                        'number': '',
                        'name': payment['name'],
                        'debit': payment['amount'] if report_type == 'out_invoice' else '0.0',
                        'credit': payment['amount'] if report_type == 'in_invoice' else '0.0',
                        'amount_residual': item.amount_residual,
                        'no_document': '-',
                        'document_value': payment['amount'],
                    })

        return lines_return

    def action_report(self):
        list_data = self._lines(self.env.context['types'])
        output = io.BytesIO()

        workbook = xlwt.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_sheet('Estado de cuenta')
        cabecera = xlwt.easyxf('font: name Times New Roman, color-index black, bold on',
                               num_format_str='#,##0.00')
        document = xlwt.easyxf('font: name Times New Roman, color-index blue, bold on',
                               num_format_str='#,##0.00')
        worksheet.write(3, 0, 'Fecha', cabecera)
        worksheet.write(3, 1, 'Tipo', cabecera)
        worksheet.write(3, 2, 'Documento', cabecera)
        worksheet.write(3, 3, 'Concepto', cabecera)
        worksheet.write(3, 4, 'Debe', cabecera)
        worksheet.write(3, 5, 'Haber', cabecera)
        worksheet.write(3, 6, 'Saldo', cabecera)
        worksheet.write(3, 7, 'Doc. Contable', cabecera)
        worksheet.write(3, 8, 'Valor Doc', cabecera)
        worksheet.write(3, 9, 'N° Cobro', cabecera)
        line = 4
        for row in list_data:
            worksheet.write(line, 0, row['date'], document)
            worksheet.write(line, 1, row['type'], document)
            worksheet.write(line, 2, row['no_document'], document)
            worksheet.write(line, 3, row['name'], document)
            worksheet.write(line, 4, row['debit'], document)
            worksheet.write(line, 5, row['credit'], document)
            worksheet.write(line, 6, row['amount_residual'], document)
            worksheet.write(line, 7, row['number'], document)
            worksheet.write(line, 8, row['document_value'], document)
            worksheet.write(line, 9, '', document)
            line += 1

        # Guarda el libro de trabajo en un archivo
        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)

        # Obtiene el contenido del archivo generado
        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        export_id = self.env['download.xlsx'].create(
            {'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': 'Estado de cuentas.xls'})
        fp.close()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'download.xlsx',
            'view_type': 'form',
            'target': 'new',

        }
