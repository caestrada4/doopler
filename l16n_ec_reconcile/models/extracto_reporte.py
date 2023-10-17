# -*- coding: utf-8 -*-
# © <2019> <Danner Marante Jacas>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class extracto_reporte(models.AbstractModel):
    _name = 'report.l16n_ec_reconcile.extracto_reporte'
    _auto = False

    ## listado de cheques girados y no cobrados a la fecha de cierre del extracto
    def _list_cheqes_no_cobrados(self, account_id, date_stop, ):
        sql = """
               select bal.date,bal.number ,bal.value,pr.name
               from bnc_initial_balances bal
               left join res_partner pr on bal.partner_id = pr.id
               where bal.company_id = %s and (bal.conciliate = false or bal.conciliate_date >= '%s') 
               and bal.account_id = %s order by bal.date
               """ % (self.env.user.company_id.id, date_stop, account_id)

        self.env.cr.execute(sql)
        saldo_carga_inicial = self.env.cr.dictfetchall()
        total = 0.0
        lista_mes = []
        list_mese_anterioreres = []
        for re in saldo_carga_inicial:
            if re['date'] == date_stop:
                lista_mes.append({
                    'move_name': re['number'],
                    'date': re['date'],
                    'balance': abs(re['value']),
                    'name': re['name']
                })
            else:
                list_mese_anterioreres.append({
                    'move_name': re['number'],
                    'date': re['date'],
                    'balance': abs(re['value']),
                    'name': re['name']
                })
            total += abs(re['value'])
        return total, lista_mes, list_mese_anterioreres

    def _list_no_concilied(self, account, date):

        total = 0.0
        lista_mes = []
        list_mese_anterioreres = []
        total, lista_mes, list_mese_anterioreres = self._list_cheqes_no_cobrados(account, date)

        sql = """ SELECT par.name,mov.name move_name,lin.date, lin.balance
                FROM account_move_line lin
                left join res_partner par on par.id = lin.partner_id
                inner join account_move mov
                on mov.id = lin.move_id
                WHERE lin.account_id = %s
                AND lin.date <= '%s' and (conciled = false or conciled is null or conciled_date > '%s') order by lin.date
             """ % (account, date,date)
        self.env.cr.execute(sql)
        list = self.env.cr.dictfetchall()

        for li in list:
            total += li['balance'] * -1
            li['balance'] = li['balance'] * -1
            if li['date'] == date:
                lista_mes.append(li)
            else:
                list_mese_anterioreres.append(li)

        return total, lista_mes, list_mese_anterioreres

    @api.model
    def _get_report_values(self, docids, data):
        # self.model = self.env.context.get('active_model')
        extraxto = self.env['account.bank.reconcile'].browse(docids)

        total_mov, list_mov_noconciliados, list_mov_noconciliados_mese = self._list_no_concilied(
            extraxto.journal_id.default_account_id.id,
            extraxto.date_stop)

        return {
            'doc_ids': self.ids,
            # 'doc_model': self.model,
            'docs': extraxto,
            # 'cheques_no_cobrados': list_cheques,
            # 'total_cheques': total,
            'list_mov_noconciliados': list_mov_noconciliados,
            'list_mov_noconciliados_mes': list_mov_noconciliados_mese,
            'total_mov': total_mov,
        }
