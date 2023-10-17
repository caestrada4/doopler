# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import calendar
import os
import time
from odoo import fields, models
from jinja2 import Environment, FileSystemLoader
from odoo.exceptions import ValidationError
from odoo.tools import date_utils


def get_years():
    year_list = []
    for i in range(int(time.strftime("%Y")) - 5, int(time.strftime("%Y")) + 2):
        year_list.append((str(i), str(i)))
    return year_list

class AnexoTransac(models.Model):
    _name = "l16n.reporte.trans"
    # _order = "create_date desc"

    fact_manual = fields.Boolean('Facturación Manual', default=False)
    
    month = fields.Selection([('1', u'Enero'), ('2',u'Febrero'),
                              
                              ('3', u'Marzo'), ('4', u'Abril'),
                              ('5', u'Mayo'), ('6', u'Junio'),
                              ('7',u'Julio'), ('8', u'Agosto'),
                              ('9', u'Septiembre'), ('10', u'Octubre'), 
                              ('11', u'Noviembre'), ('12', u'Diciembre')
                              ],
                             string='Mes',
                             default='1'
                             )

    year = fields.Selection(get_years(), string='Año')
    
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        change_default=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user.company_id.id  # noqa
    )

    txt_filename = fields.Char()
    txt_binary = fields.Binary()
    fact_manual = fields.Boolean('Facturación Manual', default=False)

    TEMPLATES = {
        'anexo_transaccional': 'anexo_transaccional.xml'
    }

    TIPO_IDENTIFICACION_GENERAL = {
        'pasaporte': 'P',
        'cedula': 'C',
        'RUC': 'R'
    }
    TIPO_IDENTIFICACION = {
        'pasaporte': '03',
        'Cédula': '02',
        'RUC': '01'
    }
    TP_ID_CLIENTE = {
        'pasaporte': '06',
        'cedula': '05',
        'RUC': '04'
    }

    CARACTERES_PERRMITIDOS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890 '
    
    def formato_fecha(self, par):
        fecha = "%s/%s/%s" % (str(par.day).zfill(2), str(par.month).zfill(2), par.year)
        return fecha
    
    def _lista_notas_credito(self, dateMonthStart, dateMonthEnd):
        list_notas = self.env['account.move'].search([('state', 'in', ['paid', 'open'])
                                                            , ('company_id', '=', self.env.user.company_id.id)
                                                            , ('invoice_date', '>=', dateMonthStart),
                                                         ('invoice_date', '<=', dateMonthEnd),
                                                         ('move_type', 'in', ['out_refund'])
                                                      ])
        resul_notas = {}
        total = 0

        for notas in list_notas:
            bandera = False
            total += notas['amount_untaxed']
            try:
                resul_notas[notas.partner_id.id]['baseImpGrav'] = str(
                    "{0:.2f}".format(
                        float(resul_notas[notas.partner_id.id]['baseImpGrav']) + float(notas.amount_vat_cero)))

                resul_notas[notas.partner_id.id]['baseImpGrav'] = str("{0:.2f}".format(
                    float(resul_notas[notas.partner_id.id]['baseImponible']) + float(notas.amount_vat_cero)))
                resul_notas[notas.partner_id.id]['baseImpGrav'] = str(
                    "{0:.2f}".format(float(resul_notas[notas.partner_id.id]['baseImpGrav']) + float(notas.amount_vat)))
                resul_notas[notas.partner_id.id]['montoIce'] = str(
                    "{0:.2f}".format(float(resul_notas[notas.partner_id.id]['montoIce']) + notas.amount_ice))
                resul_notas[notas.partner_id.id]['montoIva'] = str(
                    "{0:.2f}".format(float(resul_notas[notas.partner_id.id]['montoIva']) + notas.amount_tax))

                valorIva = float(resul_notas[notas.partner_id.id]['valorRetIva'])
                retRent = float(resul_notas[notas.partner_id.id]['valorRetRenta'])

                if notas.retention_id:
                    if notas.retention_id.state == 'done':
                        for impu in notas.retention_id.tax_ids:
                            if impu.tax_id.tax_group_id.code == 'ret_ir':
                                retRent += abs(impu.amount)
                            if impu.tax_id.tax_group_id.code in ['ret_vat_srv', 'ret_vat_b']:
                                valorIva += abs(impu.amount)

                resul_notas[notas.partner_id.id]['numeroComprobantes'] += 1
                resul_notas[notas.partner_id.id]['valorRetIva'] = str("{0:.2f}".format(valorIva))
                resul_notas[notas.partner_id.id]['valorRetRenta'] = str("{0:.2f}".format(retRent))

            except Exception:
                resul_notas[notas.partner_id.id] = {}
                resul_notas[notas.partner_id.id].update(
                    {'tpIdCliente': self.TP_ID_CLIENTE[notas.partner_id.type_identifier]})
                resul_notas[notas.partner_id.id].update({'idCliente': str(notas.partner_id.identifier)})
                resul_notas[notas.partner_id.id].update({'parteRelVtas': 'NO'})
                resul_notas[notas.partner_id.id].update({'tipoComprobante': str(notas.auth_inv_id.type_id.code)})
                if self.env.user.company_id.type_invoice == '1':
                    resul_notas[notas.partner_id.id].update({'tipoEmision': 'E'})
                else:
                    resul_notas[notas.partner_id.id].update({'tipoEmision': 'F'})
                resul_notas[notas.partner_id.id].update({'numeroComprobantes': 1})
                resul_notas[notas.partner_id.id].update({'baseNoGraIva': '0.00'})
                resul_notas[notas.partner_id.id].update({'baseImponible': str("{0:.2f}".format(notas.amount_vat_cero))})
                resul_notas[notas.partner_id.id].update({'baseImpGrav': str("{0:.2f}".format(notas.amount_vat))})
                resul_notas[notas.partner_id.id].update({'montoIce': str("{0:.2f}".format(notas.amount_ice))})
                resul_notas[notas.partner_id.id].update({'montoIva': str("{0:.2f}".format(notas.amount_tax))})
                valorIva = 0.0
                retRent = 0.0
                if notas.retention_id:
                    if notas.retention_id.state == 'done':
                        for impu in notas.retention_id.tax_ids:
                            if impu.tax_id.tax_group_id.code == 'ret_ir':
                                retRent += abs(impu.amount)
                            if impu.tax_id.tax_group_id.code in ['ret_vat_srv', 'ret_vat_b']:
                                valorIva += abs(impu.amount)
                resul_notas[notas.partner_id.id]['valorRetIva'] = str("{0:.2f}".format(valorIva))
                resul_notas[notas.partner_id.id]['valorRetRenta'] = str("{0:.2f}".format(retRent))

        return total, resul_notas

    

    def lista_compras(self, dateMonthStart, dateMonthEnd):
        list_compras = []

        compras = self.env['account.move'].search([
            # ('state', 'in', ['posted', 'open']),
                                                        ('company_id', '=', 2),
                                                        ('invoice_date', '>=', dateMonthStart),
                                                        ('invoice_date', '<=', dateMonthEnd),
                                                        ('move_type', 'in', ['in_invoice', 'liq_purchase']),
                                                        ('off_accounting', '=', False)
                                                      ]
                                                  )

        for comp in compras:
            temp = {}
            temp.update({'codSustento': str(comp.sustento_sri.code)})
            temp.update({'tpIdProv': str(self.TIPO_IDENTIFICACION[comp.partner_id.l10n_latam_identification_type_id.name])})
            temp.update({'idProv': str(comp.partner_id.vat)})
            parteRel = 'NO'
            # if comp.partner_id.parte_rel:
            #     parteRel = 'SI'
            temp.update({'parteRel': str(parteRel)})

            temp.update({'tipoComprobante': str(comp.l10n_latam_document_type_id.code)})
            temp.update({'tipoProv': False})
            if self.TIPO_IDENTIFICACION[comp.partner_id.l10n_latam_identification_type_id.name] == '03':
                tipoProv = '01'
                if comp.partner_id.company_type == 'company':
                    tipoProv = '02'
                temp.update({'tipoProv': tipoProv})
                temp.update({'denoProv':  self.update_razon_social(comp.partner_id.name)})

            temp.update({'fechaRegistro': self.formato_fecha(comp.invoice_date)})
            temp.update({'establecimiento': str(comp.journal_id.l10n_ec_entity)})
            temp.update({'puntoEmision': str(comp.journal_id.l10n_ec_emission)})
            if len(comp.l10n_latam_document_number) == 15:
                temp.update({'secuencial': str(comp.reference[6:15])})
                temp.update({'establecimiento': str(comp.reference[0:3])})
                temp.update({'puntoEmision': str(comp.reference[3:6])})
            else:
                temp.update({'secuencial': str(comp.l10n_latam_document_number)})
            temp.update({'fechaEmision': str(self.formato_fecha(comp.invoice_date))})
            if comp.move_type =='liq_purchase':
                if not comp.authorization_number:
                    raise ValidationError(
                        u'El documento de liquidacion de compra ' + comp.internal_inv_number + u' no tiene clave de acceso')
                temp.update({'autorizacion': str(comp.authorization_number)})
            else:
                if not comp.authorization_number:
                    raise ValidationError(
                        "La factura de compra {} no tiene clave de acceso".format(comp.internal_inv_number))
                temp.update({'autorizacion': str(comp.authorization_number)})

            temp.update({'baseNoGraIva': '0.00'})
            # str("{0:.2f}".format(comp.amount_vat_cero))}) # viene los valores con iva 0 o sin iva
            # temp.update({'baseImponible': str("{0:.2f}".format(comp.amount_vat_cero))})
            # temp.update({'baseImpGrav': str("{0:.2f}".format(comp.amount_vat))})
            # temp.update({'baseImpExe': '0.00'})
            # temp.update({'montoIce': str("{0:.2f}".format(comp.amount_ice))})
            # temp.update({'montoIva': str("{0:.2f}".format(comp.amount_tax))})
            totbasesImpReemb = 0
            if comp.amount_paid >= 1000:
                fpago = 'VALIDAR FACTURA'
                if comp.epayment_id:
                    fpago = comp.sustento_sri.code
                temp.update({'formaPago': fpago})
            if comp.sustento_sri.code == '08':
                totbasesImpReemb = comp.amount_vat_cero

            temp.update({'totbasesImpReemb': str("{0:.2f}".format(totbasesImpReemb))})
            valorRetBienes = 0
            retBienes10 = 0
            valRetServ20 = 0
            valRetServ50 = 0
            valorRetServicios = 0
            valRetServ100 = 0
            retencion = self.env['account.retention'].search([('invoice_id', '=', comp.id), ('state', '=', 'done')])

            impu_retencion = []
            for re in retencion:
                retBienes10 += re.val_ret_bien_10
                valRetServ20 += re.val_ret_serv_20
                valorRetBienes += re.val_ret_bienes
                valRetServ50 += re.val_ret_serv_50
                valorRetServicios += re.val_ret_serv
                valRetServ100 += re.val_ret_serv_100
                totalAmount = 0
                temp.update({'totalAmount': False})
                for impu in re.move_ids:
                    if impu.tax_id.tax_group_id.l10n_ec_type != 'withhold_vat':
                        existe = False
                        for temimpu in impu_retencion:
                            if temimpu['codRetAir'] == impu.tax_id.description:
                                existe = True
                                temimpu['baseImpAir'] = "{0:.2f}".format(float(temimpu['baseImpAir']) + abs(impu.base))
                                temimpu['valRetAir'] = "{0:.2f}".format(float(temimpu['valRetAir']) + abs(impu.amount))
                                continue
                        if not existe:
                            temp1 = {}
                            temp1.update({'codRetAir': impu.tax_id.description})
                            temp1.update({'baseImpAir': str("{0:.2f}".format(impu.base))})
                            temp1.update({'porcentajeAir': impu.tax_id.percent_report})
                            temp1.update({'valRetAir': str("{0:.2f}".format(abs(impu.amount)))})
                            impu_retencion.append(temp1)
                        totalAmount = totalAmount + abs(impu.amount)
                temp.update({'estabRetencion1': str(re.l10n_ec_retention_emission)})
                temp.update({'ptoEmiRetencion1': str(re.l10n_ec_retention_entity)})
                if re.name:
                    temp.update({'secRetencion1': str(re.name[6:len(re.name)])})
                else:
                    temp.update({'secRetencion1': ''})
                    temp.update({'autRetencion1': str(re.authorization_number)})
            

                temp.update({'fechaEmiRet1': self.formato_fecha(re.date)})

                if totalAmount != 0:
                    temp.update({'totalAmount': True})

            temp.update({'detalleAir': impu_retencion})

            temp.update({'valRetBien10': str("{0:.2f}".format(abs(retBienes10)))})
            temp.update({'valRetServ20': str("{0:.2f}".format(abs(valRetServ20)))})
            temp.update({'valorRetBienes': str("{0:.2f}".format(abs(valorRetBienes)))})
            temp.update({'valRetServ50': str("{0:.2f}".format(abs(valRetServ50)))})
            temp.update({'valorRetServicios': str("{0:.2f}".format(abs(valorRetServicios)))})
            temp.update({'valRetServ100': str("{0:.2f}".format(abs(valRetServ100)))})
            list_compras.append(temp)

        return list_compras
    

    def update_razon_social(self, par):
        temp_param = ''
        list = par.upper()
        for car in list:
            if self.CARACTERES_PERRMITIDOS.find(car) != -1:
                temp_param = temp_param + car
        return temp_param


    def generate_file(self):
        try:
            tmpl_path = os.path.join(os.path.dirname(__file__), 'template')
            env = Environment(loader=FileSystemLoader(tmpl_path))
            anexo_template = env.get_template(self.TEMPLATES['anexo_transaccional'])

            dateMonthStart = "%s-%s-01" % (str(self.year), str(self.month))
            dateMonthEnd = "%s-%s-%s" % (str(self.year), str(self.month), calendar.monthrange(int(self.year), int(self.month))[1])

            compras = self.lista_compras(dateMonthStart, dateMonthEnd)

            ventas = 0
            list_ventas = []#self.lista_ventas(dateMonthStart, dateMonthEnd)

            
            data = {}
            data.update({'id_informante': self.env.user.company_id.partner_id.vat})
            data.update(
                {'tipo_documento': self.TIPO_IDENTIFICACION_GENERAL[self.env.user.company_id.partner_id.l10n_latam_identification_type_id.name]})

            data.update({'razon_social': self.update_razon_social(self.env.user.company_id.partner_id.name)})
            data.update({'manual': True})
            data.update({'anio': self.year})
            data.update({'mes': str(self.month).zfill(2)})
            data.update({'totalVentas': "{0:.2f}".format(ventas)})
            data.update({'codigoOperativo': 'IVA'})
            data.update({'list_compras': compras})
            data.update({'list_ventas': list_ventas})
            

            anexo = anexo_template.render(data)

            return self.write({
                'txt_filename': 'Anexo Transaccional.xml',
                'txt_binary': base64.standard_b64encode(anexo.encode('utf-8'))
            })
        except Exception as e:
            raise ValidationError(u'Error al generar el archivo XML: %s' % e)
        
    def name_get(self):
        result = []
        for cat in self:
            name = cat.year + '-' + cat.month
            result.append((cat.id, name))
        return result