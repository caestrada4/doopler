# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import calendar
import copy
import datetime

import xlrd

from odoo import api, fields, models, _
from odoo.exceptions import (UserError)


class AccountBankReconcile(models.Model):
    _name = 'account.bank.reconcile'
    _order = 'date_start DESC'

    def unlink(self):
        for ob in self:
            if ob.state != 'draft':
                raise UserError(_('No puede eliminar un documento validado.'))
            for li in self.extracto_ids:
                if li.move_id:
                    li.move_id.conciled = False
                    li.move_id.conciled_date = None
                li.unlink()
        super(AccountBankReconcile, self).unlink()
        return True

    @api.model
    def _default_date_start(self):
        today = datetime.date.today()
        today = today.replace(day=1)
        res = fields.Date.to_string(today)
        return res

    @api.model
    def _default_date_stop(self):
        today = datetime.date.today()
        first, last = calendar.monthrange(today.year, today.month)
        today = today.replace(day=last)
        res = fields.Date.to_string(today)
        return res

    @api.onchange('journal_id', 'date_stop')
    def _balance_carga_inicial(self):
        for ban in self:
            try:
                if ban.journal_id.default_debit_account_id.id:
                    sql = """
                        select  sum(value)
                        from bnc_initial_balances
                        where company_id = %s and (conciliate = false or conciliate_date >= '%s' ) 
                        and account_id = %s 
                        """ % (ban.env.user.company_id.id, ban.date_stop,
                               ban.journal_id.default_debit_account_id.id)
                    self.env.cr.execute(sql)
                    saldo_carga_inicial = self.env.cr.dictfetchone()
                    ban.balance_carga_inicial = saldo_carga_inicial['sum']
                else:
                    ban.balance_carga_inicial = 0.0
            except Exception:
                ban.balance_carga_inicial = 0.0

    @api.onchange('journal_id', 'date_start')
    def _initial_balance(self):
        for ban in self:
            try:
                if self.journal_id.default_debit_account_id and self.date_start:
                    sql = """
                         SELECT account_id AS id,
                         SUM(debit) AS debit, 
                         SUM(credit) AS credit, 
                         (SUM(debit) - SUM(credit)) AS balance 
                         FROM account_move as account_move_line__move_id,
                         account_move_line 
                         WHERE account_id =%s
                         AND (account_move_line.move_id = account_move_line__move_id.id) 
                         AND account_move_line.date <= '%s'
                         GROUP BY account_id 
                         """ % (ban.journal_id.default_debit_account_id.id, ban.date_start)

                    self.env.cr.execute(sql)
                    saldo_final = self.env.cr.dictfetchone()
                    ban.balance_start = saldo_final['balance']
                else:
                    ban.balance_start = 0.0
            except Exception:
                ban.balance_start = 0.0

    @api.onchange('journal_id', 'date_stop')
    def _end_balance(self):
        for ban in self:
            try:
                if self.journal_id.default_debit_account_id and self.date_stop:
                    sql = """
                                SELECT account_id AS id,
                                SUM(debit) AS debit, 
                                SUM(credit) AS credit, 
                                (SUM(debit) - SUM(credit)) AS balance 
                                FROM account_move as account_move_line__move_id,
                                account_move_line 
                                WHERE account_id =%s
                                AND (account_move_line.move_id = account_move_line__move_id.id) 
                                AND account_move_line.date <= '%s'
                                GROUP BY account_id 
                                """ % (ban.journal_id.default_debit_account_id.id, ban.date_stop)

                    self.env.cr.execute(sql)
                    saldo_final = self.env.cr.dictfetchone()
                    ban.balance_stop = saldo_final['balance']

                else:
                    ban.balance_stop = 0.0
            except Exception:
                ban.balance_stop = 0.0

    name = fields.Char(
        'Codigo',
        required=True,
        default='/',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    journal_id = fields.Many2one(
        'account.journal',
        'Banco',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    date_start = fields.Date(
        'Desde',
        required=True,
        default=_default_date_start,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    date_stop = fields.Date(
        'Hasta',
        required=True,
        default=_default_date_stop,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    balance_start = fields.Float(
        'Balance Inicial',
        required=True,
        compute='_initial_balance',
        # default=_initial_balance,
        readonly=True,
        # store=True,
    )

    balance_stop = fields.Float(
        'Balance Final',
        required=True,
        compute=_end_balance,
        readonly=True,
        # store=True,

    )

    balance_carga_inicial = fields.Monetary(
        'Cheques Girados y no Cobrados',
        required=True,
        compute=_balance_carga_inicial,
        readonly=True
    )

    balance_banco = fields.Monetary(
        'Saldo Banco',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    currency_id = fields.Many2one(
        'res.currency',
        'Moneda'
    )
    line_ids = fields.One2many(
        'account.move.line',
        'concile_id',
        'Detalle'
    )

    extracto_ids = fields.One2many(
        'extracto.bancario',
        'concile_id',
        'Detalle'
    )

    #   listExt = fields.

    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('done', 'Realizado')
        ],
        string='Estado',
        required=True,
        default='draft'
    )

    excel_file = fields.Binary('Conciliacion')
    file_name = fields.Char('File Name')

    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        change_default=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('account.invoice')  # noqa
    )

    def _parser_json_line(selef, account):
        return {
            'cuenta': account.account_id.display_name,
            'fecha': account.date,
            'name': account.name,
            'ref': account.ref,
            'id': account.id,
            'credit': "{0:.2f}".format(account.credit),
            'debit': "{0:.2f}".format(account.debit),
            'conciliar': [],
            'total': 0,
            'select': []
        }

    def _parser_json_extracto(selef, ext):
        return {
            'cuenta': ext.oficina,
            'fecha': ext.date,
            'name': ext.concepto,
            'ref': ext.referencia,
            'id1': str(ext.id),
            'credit': "{0:.2f}".format(ext.haber),
            'debit': "{0:.2f}".format(ext.debe),
            'conciliar': []
        }

    def _parser_json_saldo_inicial(selef, ext):
        return {
            'cuenta': ext.account_id.display_name,
            'fecha': ext.date,
            'name': ext.concepto,
            'ref': 'Cheques girados y no cobrados',
            'id': 'initial_' + str(ext.id),
            'credit': "{0:.2f}".format(ext.value),
            'debit': "0.0",
            'conciliar': [],
            'total': 0,
            'select': []
        }

    @api.model
    def list_conciliacion(self, banco, limit):

        sql = """ select rec.date_stop from account_bank_reconcile rec 
                   inner join account_journal jou on jou.id = rec.journal_id
                   where jou.default_account_id =%s and state = 'draft' 
                   order by date_stop desc              
                   """ % (banco)

        self._cr.execute(sql)
        res = self._cr.fetchone()
        if res:
            not_conciled = self.env['account.move.line'].search([
                ('account_id', '=', int(banco)), ('conciled', '=', False),
                ('date', '<=', res[0])
            ])

            list_no_concilied = []
            list_extracto_credit = []
            list_extracto_debit = []

            total_dedito = 0
            total_credito = 0

            extracto_credit = self.env['extracto.bancario'].search([('account_id', '=', int(banco)),
                                                                    ('type', '=', 'ext'), ('debe', '<>', 0),
                                                                    ('conciliado', '=', False), ('date', '<=', res[0])
                                                                    ], order="date desc")

            extracto_debit = self.env['extracto.bancario'].search([('account_id', '=', int(banco)),
                                                                   ('type', '=', 'ext'), ('haber', '<>', 0),
                                                                   ('conciliado', '=', False), ('date', '<=', res[0])
                                                                   ], order="date desc")

            for account in not_conciled:
                list_no_concilied.append(self._parser_json_line(account))

            for ext in extracto_credit:
                list_extracto_credit.append(self._parser_json_extracto(ext))

            for ext in extracto_debit:
                list_extracto_debit.append(self._parser_json_extracto(ext))


            list_no_coinciden = []
            list_coinciden = []
            dif_permitida = 0.00001

            for account in list_no_concilied:
                bandera = True
                for ext1 in list_extracto_debit:
                    ext = copy.copy(ext1)
                    ext['id'] = str(account['id']) + '-' + str(ext['id1'])

                    if abs(float(ext['credit']) - float(account['debit'])) < dif_permitida and float(ext['credit']) > 0:
                        account['select'].append(ext)
                        account['conciliar'] = []
                        try:
                            account['total'] += float(ext1['credit'])
                        except Exception as e:
                            account['total'] = 0.0
                            account['total'] += float(ext1['credit'])
                        list_extracto_debit.remove(ext1)
                        bandera = False
                        # break

                for ext1 in list_extracto_credit:
                    ext = copy.copy(ext1)
                    ext['id'] = str(account['id']) + '-' + str(ext['id1'])
                    if abs(float(ext['debit']) - float(account['credit'])) < dif_permitida and float(ext['debit']) > 0:
                        account['select'].append(ext)
                        account['conciliar'] = []

                        try:
                            account['total'] += float(ext['debit'])
                        except Exception as e:
                            account['total'] = 0.0
                            account['total'] += float(ext1['debit'])
                        list_extracto_credit.remove(ext1)
                        bandera = False
                        # break

                total_dedito = total_dedito + float(account['debit'])
                total_credito = total_credito + float(account['credit'])
                if bandera:
                    account1 = copy.copy(account)
                    list_no_coinciden.append(account1)
                else:
                    account1 = copy.copy(account)
                    list_coinciden.append(account1)
            cant = 0

            for noc in list_no_coinciden:
                noc1 = copy.copy(noc)
                if float(noc1['debit']) > 0:
                    for deb in list_extracto_debit:
                        deb1 = copy.copy(deb)
                        deb1['id'] = str(noc1['id']) + '-' + str(deb['id1'])
                        noc1['conciliar'].append(deb1)

                if float(noc1['credit']) > 0:
                    for deb in list_extracto_credit:
                        deb1 = copy.copy(deb)
                        deb1['id'] = str(noc1['id']) + '-' + str(deb['id1'])
                        noc1['conciliar'].append(deb1)

                list_coinciden.append(noc1)

            cantidad = len(list_coinciden)
            if cantidad > int(limit):
                list_coinciden = list_coinciden[0: int(limit)]
            return {
                'account': list_coinciden,
                'credit': total_credito,
                'debit': total_credito
            }
        else:
            raise UserError(u'Importe una conciliación para esta cuenta')

    @api.model
    def bancos(self):
        try:
            bancos = self.env['account.journal'].search([('company_id', '=', self.env.user.company_id.id),
                                                         ('type', '=', 'bank')])
            resul = []
            for ban in bancos:
                resul.append({
                    'id': ban.default_account_id.id,
                    'name': ban.name
                })
            return resul
        except Exception:
            raise UserError(_('Error en el proceso.'))

    @api.model
    def automatic_conciliacion(self, limit, cuenta):
        list = self.list_conciliacion(cuenta, limit)
        for lin in list['account']:
            if len(lin['select']) > 0:
                resul = self.conciliar(lin)
        a = 1

    @api.model
    def conciliar(self, data):
        valoresincorrectos = False
        try:
            carga_inicial = False
            if str(data['id']).find('initial_') == -1:
                mov = self.env['account.move.line'].search([
                    ('id', '=', data['id'])])
            else:
                id_line = data['id']
                index = id_line.find('_')
                id_line = data['id'][index + 1: len(id_line)]
                carga_inicial = True

            lines = []
            debe = 0
            credito = 0
            fecha_conciliacion = None
            for val in data['select']:
                debe += float(val['debit'])
                credito += float(val['credit'])
            dif_permitida = 0.00001

            if abs(float(data['debit']) - credito) < dif_permitida and abs(
                    float(data['credit']) - debe) < dif_permitida:
                ids = ''
                ids_cargas_iniciales = ''

                for sel in data['select']:
                    id_line = sel['id']
                    index = id_line.find('-')
                    id_line = id_line[index + 1: len(id_line)]
                    ids += id_line + ','
                    fecha_conciliacion = sel['fecha']

                if ids.find(',') != -1:
                    fin = len(ids) - 1
                    ids = ids[0:fin]

                if ids:
                    if carga_inicial:
                        sql = """update extracto_bancario
                                 set conciliado = true
                                 where id in (%s)
                                 """ % (ids)
                    else:
                        sql = """update extracto_bancario
                             set conciliado = true,
                             move_id = %s
                             where id in (%s)
                             """ % (mov.id, ids)
                    self.env.cr.execute(sql)

                if carga_inicial:
                    mov.update({
                        'conciliate': True,
                        'conciliate_date': data['select'][0]['fecha']
                    })
                else:
                    if not fecha_conciliacion:
                        fecha_conciliacion = data['fecha']
                    mov.update({'conciled': True})
                    mov.update({'conciled_date': fecha_conciliacion})
            else:
                valoresincorrectos = True
                raise UserError(_('Los valores a conciliar no son correctos.'))
        except:
            if valoresincorrectos:
                raise UserError(_('Los valores a conciliar no son correctos.'))
            raise UserError(_('Error en el proceso.'))

    def export(self):
        error = 0
        # try:
        self.ensure_one()
        # if self.journal_id.template_reconcilie == 'pichincha':
        self._parse_file_pichincha(base64.b64decode(self.excel_file))
        # elif self.journal_id.template_reconcilie == 'pacifico':
        #     self._parse_file_pacifico(base64.b64decode(self.excel_file))
        # else:
        #
        #     raise UserError(_('Seleccione en el diario la plantilla que desea importar.'))

    # except Exception:
    #    raise UserError(_('Error en el proceso.'))

    # Importa el template del banco pichincha

    def _parse_file_pichincha(self, data_file):
        try:
            wb = xlrd.open_workbook(file_contents=data_file)
            lines = []
            index = 0
            for s in wb.sheets():
                for row in range(s.nrows):
                    index += 1
                    if row > 0:
                        data_row = []
                        for col in range(s.ncols):
                            value = str((s.cell(row, col).value))
                            data_row.append(value)

                        try:
                            fecha1 = float(data_row[0])
                            utc_days = fecha1 - 25569
                            utc_value = utc_days * 86400
                            fecha1 = str(datetime.datetime.fromtimestamp(utc_value))

                        except Exception:
                            fecha1 = data_row[0]
                            fecha1 = fecha1.replace('/', '-')
                            fecha1 = fecha1[0:10]
                            fecha = fecha1.split('-')
                            fecha1 = datetime.date(int(fecha[2]), int(fecha[0]), int(fecha[1]))

                        haber = 0
                        debe = 0
                        tipo_ingreso = data_row[3]

                        if tipo_ingreso == 'D':
                            debe = data_row[6]
                        if tipo_ingreso == 'C':
                            haber = data_row[6]

                        codigo = data_row[1]
                        eliminar_caracter = codigo.find('.')
                        codigo = codigo[0:eliminar_caracter]
                        referencia = data_row[4]
                        eliminar_caracter = referencia.find('.')
                        referencia = referencia[0:eliminar_caracter]

                        ext = {
                            'date': fecha1,
                            'codigo': codigo,
                            'concepto': str(data_row[2]).lstrip(),
                            'referencia': referencia,
                            'oficina': str(data_row[5]).lstrip(),
                            'debe': debe,
                            'haber': haber,
                            'conciliado': False,
                            'account_id': self.journal_id.default_account_id.id,
                            'concile_id': self.id,
                            'type': 'ext'
                        }
                        self.env['extracto.bancario'].create(ext)
            return True, ''
        except Exception as e:
            return False, e.args[0]


    def action_load_entries(self):
        try:
            for obj in self:
                # obj.line_ids.unlink()
                domain = [
                    ('date', '>=', self.date_start),
                    ('date', '<=', self.date_stop),
                    ('account_id', '=', self.journal_id.default_debit_account_id.id),  # noqa
                    ('conciled', '=', True)
                ]
                lines = self.env['account.move.line'].search(domain)

                not_conciled = self.env['account.move.line'].search([
                    ('date', '>=', self.date_start),
                    ('date', '<=', self.date_stop),
                    ('account_id', '=', self.journal_id.default_debit_account_id.id),  # noqa
                    ('conciled', '=', False)
                ])

                lines.write({'concile_id': obj.id})

                not_conciled.write({'concile_id': obj.id})

            for lines in self.line_ids:
                ext = {
                    'date': lines.date,
                    'codigo': lines.ref,
                    'concepto': lines.name,
                    'referencia': lines.ref,
                    # 'oficina': str(data_row[5]).lstrip(),
                    'debe': lines.debit,
                    'haber': lines.credit,
                    'conciliado': False,
                    'account_id': self.journal_id.default_debit_account_id.id,
                    'concile_id': self.id,
                    'type': 'move'
                }
                self.env['extracto.bancario'].create(ext)

            return True
        except Exception:
            raise UserError(_('Los datos importados no son correctos.'))

    def _mov_no_conculiate(self):
        try:

            sql = """ SELECT account_id AS id,
                         SUM(debit) AS debit, 
                         SUM(credit) AS credit, 
                         (SUM(debit) - SUM(credit)) AS balance 
                         FROM account_move as account_move_line__move_id,
                         account_move_line 
                         WHERE account_id =%s
                         AND (account_move_line.move_id = account_move_line__move_id.id) 
                         AND account_move_line.date <= '%s' and (conciled = false or conciled is null)
                         GROUP BY account_id 
                         """ % (self.journal_id.default_debit_account_id.id, self.date_stop)

            self.env.cr.execute(sql)
            saldo_final = self.env.cr.dictfetchone()
            return saldo_final['balance']
        except Exception:
            return 0

    def action_done(self):
        for obj in self:
            line_concilied = True
            for ext in obj.extracto_ids:
                if ext.conciliado == False:
                    line_concilied = False
                    break
            if line_concilied == False:
                raise UserError('Concillie todas las entradas antes de continuar.')

            list_mov_noconcilied = self._mov_no_conculiate()

            computed = self.balance_stop + self.balance_carga_inicial + abs(list_mov_noconcilied)
            resta = obj.balance_banco - computed
            dif_permitida = 0.02
            if abs(resta) > dif_permitida:
                raise UserError('El balance final es incorrecto por $ {} .'.format(resta))
            code = self.env['ir.sequence'].next_by_code('bank.reconcile')
            obj.write({'state': 'done', 'name': code})
        return True

    def action_conciliar(self):
        list = []
        for obj in self.extracto_ids:
            if not obj.conciliado and obj.select:
                list.append(obj)

    def action_print(self):
        return self.env.ref('l16n_ec_reconcile.extracto_reporte').report_action()
    #    return self.env.ref('module_name.action_student_id_card').report_action(None, data=data)

    
        # return self.env['report']._get_report_values(
        #     self,
        #     'l16n_ec_reconcile.extracto_reporte'
        # )

        


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    conciled = fields.Boolean('Conciliado ?', default=False, copy=False)
    conciled_date = fields.Date('Fecha de Conciliacion')

    concile_id = fields.Many2one(
        'account.bank.reconcile',
        'Hoja de Conciliacion'
    )
