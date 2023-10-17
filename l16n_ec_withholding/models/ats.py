# -*- coding: utf-8 -*-
import sys
import time

from odoo.exceptions import ValidationError

reload(sys)
sys.setdefaultencoding('utf8')
from odoo import api, fields, models
import base64
import dateutil.parser
import calendar
import os
from jinja2 import Environment, FileSystemLoader

# listado de annios para el anexo transaccional
def get_years():
    year_list = []
    for i in range(int(time.strftime("%Y")) - 5, int(time.strftime("%Y")) + 2):
        year_list.append((i, str(i)))
    return year_list

#Anexo trancaccional
class AnexoTransac(models.Model):
    _name = "10lnec.ats"
    _order = "create_date desc"

    month = fields.Selection([(1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
                              (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
                              (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'), ],
                             string='Mes')
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
        'ruc': 'R'
    }
    TIPO_IDENTIFICACION = {
        'pasaporte': '03',
        'cedula': '02',
        'ruc': '01'
    }
    TP_ID_CLIENTE = {
        'pasaporte': '06',
        'cedula': '05',
        'ruc': '04'
    }

    CARACTERES_PERRMITIDOS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890 '
    #formatea la fecha de los documentos
    def formato_fecha(self, par):
        temp = dateutil.parser.parse(par)  # python 2.7
        fecha = "%s/%s/%s" % (str(temp.day).zfill(2), str(temp.month).zfill(2), temp.year)
        return fecha
    #Lista las notas de creditos para presentar en el anexo
    def _lista_notas_credito(self, dateMonthStart, dateMonthEnd):
        list_notas = self.env['account.invoice'].search([('state', 'in', ['paid', 'open'])
                                                            , ('company_id', '=', self.env.user.company_id.id)
                                                            , ('date_invoice', '>=', dateMonthStart),
                                                         ('date_invoice', '<=', dateMonthEnd),
                                                         ('type', 'in', ['out_refund'])])
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

    # devuelve diccionario con documentos de ventas
    def lista_ventas(self, dateMonthStart, dateMonthEnd):
        list_ventas = self.env['account.invoice'].search([('state', 'in', ['paid', 'open'])
                                                             , ('company_id', '=', self.env.user.company_id.id)
                                                             , ('date_invoice', '>=', dateMonthStart),
                                                          ('date_invoice', '<=', dateMonthEnd),
                                                          ('type', 'in', ['out_invoice'])])
        ventas = {}
        ventas_total = 0
        for ven in list_ventas:
            ventas_total += ven['amount_untaxed']
            try:
                ventas[ven.partner_id.id]['baseImponible'] = str("{0:.2f}".format(float(ventas[ven.partner_id.id]['baseImponible']) + float(ven.amount_vat_cero)))
                ventas[ven.partner_id.id]['baseImpGrav'] = str("{0:.2f}".format(float(ventas[ven.partner_id.id]['baseImpGrav']) + float(ven.amount_vat)))
                ventas[ven.partner_id.id]['montoIce'] = str("{0:.2f}".format(float(ventas[ven.partner_id.id]['montoIce']) + ven.amount_ice))
                ventas[ven.partner_id.id]['montoIva'] = str("{0:.2f}".format(float(ventas[ven.partner_id.id]['montoIva']) + ven.amount_tax))

                valorIva = float(ventas[ven.partner_id.id]['valorRetIva'])
                retRent = float(ventas[ven.partner_id.id]['valorRetRenta'])

                if ven.retention_id:
                    if ven.retention_id.state == 'done':
                        for impu in ven.retention_id.tax_ids:
                            if impu.tax_id.tax_group_id.code == 'ret_ir':
                                retRent += abs(impu.amount)
                            if impu.tax_id.tax_group_id.code in ['ret_vat_srv', 'ret_vat_b']:
                                valorIva += abs(impu.amount)

                ventas[ven.partner_id.id]['numeroComprobantes'] += 1
                ventas[ven.partner_id.id]['valorRetIva'] = str("{0:.2f}".format(valorIva))
                ventas[ven.partner_id.id]['valorRetRenta'] = str("{0:.2f}".format(retRent))

            except Exception:
                ventas[ven.partner_id.id] = {}
                ventas[ven.partner_id.id].update({'id': ven.id})
                ventas[ven.partner_id.id].update({'tpIdCliente': self.TP_ID_CLIENTE[ven.partner_id.type_identifier]})
                ventas[ven.partner_id.id].update({'idCliente': str(ven.partner_id.identifier)})
                ventas[ven.partner_id.id].update({'parteRelVtas': 'NO'})
                ventas[ven.partner_id.id].update({'tipoComprobante': str(ven.auth_inv_id.type_id.code)})
                if self.env.user.company_id.type_invoice == '1':
                    ventas[ven.partner_id.id].update({'tipoEmision': 'E'})
                else:
                    ventas[ven.partner_id.id].update({'tipoEmision': 'F'})

                if ven.partner_id.type_identifier == 'pasaporte':
                    ventas[ven.partner_id.id].update({'tipoCliente': '01'})
                    ventas[ven.partner_id.id].update({'nombrCliente': ven.partner_id.name})


                ventas[ven.partner_id.id].update({'numeroComprobantes': 1})
                ventas[ven.partner_id.id].update({'baseNoGraIva': '0.00'})
                ventas[ven.partner_id.id].update({'baseImponible': str("{0:.2f}".format(ven.amount_vat_cero))})
                ventas[ven.partner_id.id].update({'baseImpGrav': str("{0:.2f}".format(ven.amount_vat))})
                ventas[ven.partner_id.id].update({'montoIce': str("{0:.2f}".format(ven.amount_ice))})
                ventas[ven.partner_id.id].update({'montoIva': str("{0:.2f}".format(ven.amount_tax))})
                ventas[ven.partner_id.id].update({'formaPago': ven.epayment_id.code})

                valorIva = 0
                retRent = 0
                if ven.retention_id:
                    if ven.retention_id.state == 'done':
                        for impu in ven.retention_id.tax_ids:
                            if impu.tax_id.tax_group_id.code == 'ret_ir':
                                retRent += abs(impu.amount)
                            if impu.tax_id.tax_group_id.code in ['ret_vat_srv', 'ret_vat_b']:
                                valorIva += abs(impu.amount)
                ventas[ven.partner_id.id].update({'valorRetIva': str("{0:.2f}".format(abs(valorIva)))})
                ventas[ven.partner_id.id].update({'valorRetRenta': str("{0:.2f}".format(abs(retRent)))})

        total_notas, ventas_notas = self._lista_notas_credito(dateMonthStart, dateMonthEnd)
        ventas_total -= total_notas

        list_resul = []

        for index, valor in ventas.items():
            list_resul.append(valor)

        for index, valor in ventas_notas.items():
            list_resul.append(valor)

        if self.env.user.company_id.type_invoice == '1':
            ventas_total = 0.00
        return ventas_total, list_resul

    # devuelve diccionario con documentos de compras
    def lista_compras(self, dateMonthStart, dateMonthEnd):
        list_compras = []

        compras = self.env['account.invoice'].search([('state', 'in', ['paid', 'open']),
                                                      ('company_id', '=', self.env.user.company_id.id),
                                                      ('date_invoice', '>=', dateMonthStart),
                                                      ('date_invoice', '<=', dateMonthEnd),
                                                      ('type', 'in', ['in_invoice','liq_purchase', 'in_refund'])])

        for comp in compras:
            temp = {}
            temp.update({'codSustento': str(comp.sustento_id.code)})
            temp.update({'tpIdProv': str(self.TIPO_IDENTIFICACION[comp.partner_id.type_identifier])})
            temp.update({'idProv': str(comp.partner_id.identifier)})
            parteRel = 'NO'
            if comp.partner_id.parte_rel:
                parteRel = 'SI'
            temp.update({'parteRel': str(parteRel)})

            temp.update({'tipoComprobante': str(comp.auth_inv_id.type_id.code)})
            temp.update({'tipoProv': False})
            if self.TIPO_IDENTIFICACION[comp.partner_id.type_identifier] == '03':
                tipoProv = '01'
                if comp.partner_id.company_type == 'company':
                    tipoProv = '02'
                temp.update({'tipoProv': tipoProv})
                temp.update({'denoProv': str(comp.partner_id.name)})

            temp.update({'fechaRegistro': self.formato_fecha(comp.date_invoice)})
            temp.update({'establecimiento': str(comp.auth_inv_id.serie_entidad)})
            temp.update({'puntoEmision': str(comp.auth_inv_id.serie_emision)})
            temp.update({'secuencial': str(comp.reference)})
            temp.update({'fechaEmision': str(self.formato_fecha(comp.date_invoice))})
            if comp.type =='liq_purchase':
                if not comp.clave_acceso:
                    raise ValidationError(
                        u'El documento de liquidacion de compra ' + comp.internal_inv_number + u' no tiene clave de acceso')
                temp.update({'autorizacion': str(comp.clave_acceso)})

            else:
                if not comp.auth_number:
                    raise ValidationError(
                        "La factura de compra {} no tiene clave de acceso".format(comp.invoice_number))
                temp.update({'autorizacion': str(comp.auth_number)})
            temp.update({'baseNoGraIva': '0.00'})
            # str("{0:.2f}".format(comp.amount_vat_cero))}) # viene los valores con iva 0 o sin iva
            temp.update({'baseImponible': str("{0:.2f}".format(comp.amount_vat_cero))})
            temp.update({'baseImpGrav': str("{0:.2f}".format(comp.amount_vat))})
            temp.update({'baseImpExe': '0.00'})
            temp.update({'montoIce': str("{0:.2f}".format(comp.amount_ice))})
            temp.update({'montoIva': str("{0:.2f}".format(comp.amount_tax))})

            if comp.type =='in_refund':
                doc_origen = self.env['account.invoice'].search([('move_name','=',comp.origin)])
                if doc_origen:
                    temp.update({'estabModificado': str(doc_origen.auth_inv_id.serie_entidad)})
                    temp.update({'ptoEmiModificado': str(doc_origen.auth_inv_id.serie_emision)})
                    temp.update({'secModificado': str(doc_origen.reference)})
                    if not doc_origen.auth_number:
                        raise ValidationError(
                            u'El documento de nota de debito {} no tiene clave de acceso'.format(comp.invoice_number))
                    temp.update({'autModificado': str(doc_origen.auth_number)})

                else:
                    raise ValidationError(u'Nota de debito {} , no tiene documento que la sustente'.format(comp.name))

                # COMPR/2021/09/0219


                pass

            totbasesImpReemb = 0
            if comp.amount_pay >= 1000:
                fpago = 'VALIDAR FACTURA'
                if comp.epayment_id:
                    fpago = comp.epayment_id.code
                temp.update({'formaPago': fpago})
            if comp.sustento_id.code == '08':
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
                for impu in re.tax_ids:
                    if impu.tax_id.tax_group_id.code == 'ret_ir':
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
                temp.update({'estabRetencion1': str(re.auth_id.serie_entidad)})
                temp.update({'ptoEmiRetencion1': str(re.auth_id.serie_emision)})
                if re.name:
                    temp.update({'secRetencion1': str(re.name[6:len(re.name)])})
                else:
                    temp.update({'secRetencion1': ''})
                if re.auth_id.is_electronic:
                    if re.clave_acceso:
                        temp.update({'autRetencion1': str(re.clave_acceso)})
                    else:
                        raise ValidationError(
                            u'El documentos de retencion ' + re.name + u' no tiene clave de acceso')
                else:
                    temp.update({'autRetencion1': str(re.auth_id.name)})

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

    # devuelve diccionario con documentos anulados, para facturacion  manual
    def lista_anuladas(self, dateMonthStart, dateMonthEnd):
        list_cancelados = []
        lista = self.env['account.doc.cancel'].search([('company_id', '=', self.env.user.company_id.id),
                                                       ('date', '>=', dateMonthStart),
                                                       ('date', '<=', dateMonthEnd)])
        for comp in lista:
            anul = {}
            anul.update({'tipoComprobante': str(comp.autorization_id.type_id.code)})
            anul.update({'establecimiento': str(comp.autorization_id.serie_entidad)})
            anul.update({'puntoEmision': str(comp.autorization_id.serie_emision)})
            anul.update({'secuencialInicio': str(comp.number_start)})
            if comp.number_end:
                anul.update({'secuencialFin': str(comp.number_end)})
            else:
                anul.update({'secuencialFin': str(comp.number_start)})
            anul.update({'autorizacion': str(comp.autorization_number)})
            list_cancelados.append(anul)

        return list_cancelados

    # elimina caracteres especiales de la razon social
    def update_razon_social(self, par):
        temp_param = ''
        list = par.upper()
        for car in list:
            if self.CARACTERES_PERRMITIDOS.find(car) != -1:
                temp_param = temp_param + car
        return temp_param

    # Genera XML
    @api.one
    def generate_file(self):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'template')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        anexo_template = env.get_template(self.TEMPLATES['anexo_transaccional'])

        dateMonthStart = "%s-%s-01" % (self.year, self.month)
        dateMonthEnd = "%s-%s-%s" % (self.year, self.month, calendar.monthrange(self.year, self.month)[1])

        compras = self.lista_compras(dateMonthStart, dateMonthEnd)

        ventas, list_ventas = self.lista_ventas(dateMonthStart, dateMonthEnd)

        notas = self.lista_anuladas(dateMonthStart, dateMonthEnd)
        data = {}
        data.update({'id_informante': self.env.user.company_id.partner_id.identifier})
        data.update(
            {'tipo_documento': self.TIPO_IDENTIFICACION_GENERAL[self.env.user.company_id.partner_id.type_identifier]})

        data.update({'razon_social': self.update_razon_social(self.env.user.company_id.partner_id.name)})
        data.update({'manual': True})
        data.update({'anio': self.year})
        data.update({'mes': str(self.month).zfill(2)})
        data.update({'totalVentas': "{0:.2f}".format(ventas)})
        data.update({'codigoOperativo': 'IVA'})
        data.update({'list_compras': compras})
        data.update({'list_ventas': list_ventas})
        data.update({'detalleAnulados': notas})

        anexo = anexo_template.render(data)

        return self.write({
            'txt_filename': 'Anexo Transaccional.xml',
            'empresa': 1,
            'txt_binary': base64.standard_b64encode(anexo)
        })
