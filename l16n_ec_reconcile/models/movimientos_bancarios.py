# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import json
from io import StringIO

import  xlwt

import odoo
from odoo import api, fields, models, _
from odoo.exceptions import Warning as UserError


class MovimientosBancarios(models.TransientModel):
    _name = 'bank.account.move'

    def _lines(self, fecha_inicio, fecha_hasta, no_documento, id_select, id_valor, partner, prm_account,estados,limit=False ):
        account = """select id from account_account
                                where account_type ='asset_cash' 
                                and company_id = %s""" % (str(self.env.user.company_id.id))
        self._cr.execute(account)
        list_cuentas = self._cr.fetchall()
        cuentas = ""
        where = ""
        if fecha_inicio:
            where += "and lin.date >= '{}'".format(fecha_inicio)
        if fecha_hasta:
            where += "and lin.date <= '{}'".format(fecha_hasta)
        if no_documento:
            where += "and ( mov.name like '%{}%')".format(no_documento,no_documento)
        if id_valor:
            valor =float(id_valor)
            if id_select == 'mayor':
                where += "and  lin.balance >={} ".format(valor)
            elif id_select == 'menor':
                where += "and lin.balance <= {}".format(valor)
            else:
                where += "and round(lin.balance::numeric, 2) = {}".format(valor)
        if int(partner) != 0:
            where += " and par.id =" + partner

        if prm_account and int(prm_account) != 0:
            where += " and lin.account_id ={}".format(prm_account)
        if estados == "conciliado":
            where += " and lin.conciled = True"
        if estados == "noconciliado":
            where += " and (lin.conciled  = False or lin.conciled  is Null)"

        for acc in list_cuentas:
            if cuentas == "":
                cuentas = str(acc[0])
            else:
                cuentas += "," + str(acc[0])
        if cuentas == "":
            raise UserError(_('No hay datos para mostrar.'))

        if limit:
            limite_ofset = int(limit) * 10

            sql = """
                    select mov.name move_name, lin.date ,lin.name lin_name,lin.balance ,mov.ref, par.name par_name,
                    lin.conciled, acc.name name_account,lin.id -- ,mov.numero
                    from account_move_line lin
                    left join res_partner par
                    on par.id = lin. partner_id
                    inner join account_move mov 
                    on mov.id = move_id
                    inner join account_account acc
                    on acc.id = lin.account_id
                    -- where lin.account_id in (%s) %s
                    order by lin.id desc limit 10 offset %s
                    """ % (cuentas, where, str(limite_ofset))
        else:
            sql = """
                select mov.name move_name, lin.date ,lin.name lin_name,lin.balance ,mov.ref, par.name par_name,
                lin.conciled, acc.name name_account,lin.id 
                from account_move_line lin
                left join res_partner par
                on par.id = lin. partner_id
                inner join account_move mov 
                on mov.id = move_id
                inner join account_account acc
                on acc.id = lin.account_id
                -- where lin.account_id in (%s) %s
                order by lin.id desc
                """ % (cuentas, where)
        self._cr.execute(sql)
        list = self._cr.fetchall()
        return list

    @api.model
    def list_res_parther(self):
        sql = """
        select id,name from res_partner""" 
        self._cr.execute(sql)
        list = self._cr.fetchall()
        json_list = []
        json_list.append({
            'id': 0,
            'name': 'Todos'
        })
        for li in list:
            json_list.append({
                'id': li[0],
                'name': li[1]
            })
        return json_list

    @api.model
    def list_account(self):
        sql = """
            select id, code,name 
            from account_account
            where  company_id = %s and  account_type = 'asset_cash'
            """ % (self.env.user.company_id.id)
        self._cr.execute(sql)
        list = self._cr.fetchall()
        json_list = []
        json_list.append({
            'id': 0,
            'name': 'Todos'
        })
        for li in list:
            json_list.append({
                'id': li[0],
                'name': li[1] + ' ' + li[2]
            })
        return json_list

    def validate_number(self, valor):
        try:
            return float(valor)
        except:
            return 0
        
    @api.model
    def action_load_entries(self, fecha_inicio, fecha_hasta, no_documento,
                            select, valor, partner, account,estados,start):
        
        # raise odoo.osv.osv.except_osv('title', 'description')
        
        list = self._lines(fecha_inicio,
                           fecha_hasta, 
                           no_documento,
                           select, 
                           self.validate_number(valor) ,
                           partner,
                           int(account),
                           estados,
                           start)
        result = []
        for li in list:
            conciliado = 'No'
            if li[6]:
                conciliado = 'Si'

            result.append({
                'id':li[8],
                'date': li[1],
                'name': li[0],
                'benef': li[5],
                'concepto': li[2],
                'saldo': "{0:.2f}".format(li[3]),
                'conciliado': conciliado,
                'name_account': li[7],
                'numero': '000'#li[9]
            })

        return result


    @api.model
    def conciliar(self,id):
        mov = self.env['account.move.line'].search([('id','=',int(id))])
        mov.conciled = not mov.conciled
        if mov.conciled:
            mov.conciled_date = mov.date
        else:
            mov.conciled_date = None

        return mov.conciled




    @api.model
    def acction_export(self, fecha_inicio, fecha_hasta, no_documento, select, valor, patner, account,estados):

        workbook = xlwt.Workbook(encoding="UTF-8")
        bold = style0 = xlwt.easyxf('font: name Times New Roman, color-index red, bold on',
                                    num_format_str='#,##0.00')
        cabecera = style0 = xlwt.easyxf('font: name Times New Roman, color-index black, bold on',
                                        num_format_str='#,##0.00')
        worksheet = workbook.add_sheet('Reporte')
        worksheet.write_merge(0, 0, 0, 6, self.env.user.company_id.display_name, cabecera)
        worksheet.write_merge(1, 1, 0, 6, 'Reporte de Bancos', cabecera)

        worksheet.write(3, 0, 'Fecha', cabecera)
        worksheet.write(3, 1, 'Número de documento', cabecera)
        worksheet.write(3, 2, 'Cuenta', cabecera)
        worksheet.write(3, 3, 'Beneficiario', cabecera)
        worksheet.write(3, 4, 'Concepto', cabecera)
        worksheet.write(3, 5, 'Valor', cabecera)
        lineas = self._lines(fecha_inicio, fecha_hasta, no_documento, select, valor, patner, account,estados)
        key = 4
        for li in lineas:
            worksheet.write(key, 0, str(li[1]))
            worksheet.write(key, 1, str(li[0]))
            worksheet.write(key, 2, str(li[7]))
            worksheet.write(key, 3, str(li[5]))
            worksheet.write(key, 4, str(li[2]))
            worksheet.write(key, 5, str("{0:.2f}".format(li[3])))
            key = key + 1

        fp = StringIO()
        workbook.save(fp)
        fp.seek(0)

        export_id = self.env['excel.descargar'].create(
            {'excel_file': base64.encodestring(fp.getvalue()), 'file_name': 'Rerporte de Bancos.xls'})
        fp.close()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'excel.descargar',
            'view_type': 'form',
            'target': 'new',

        }
