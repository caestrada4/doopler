import logging
import os

from jinja2 import Environment, FileSystemLoader

from odoo import models
from odoo.exceptions import (UserError)
from . import utils
from ..xades.sri import DocumentXML
from ..xades.xades_sri import Xades


class AccountInvoice(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'account.edocument']
    _logger = logging.getLogger('account.move')
    
    TEMPLATES = {
        'out_invoice': 'out_invoice.xml',
        'out_refund': 'out_refund.xml',
        'liq_purchase': 'liq_purchase.xml'
    }

    def _info_factura(self, invoice):
        """
        Retorna la informacion de la factura
        :param invoice:
        :return:
        """
        error_mesagge = ''
        # try:
        def fix_date(date):
            d = "{}/{}/{}".format(str(date.day).zfill(2),str(date.month).zfill(2),date.year )
            return d

        company = invoice.company_id
        partner = invoice.partner_id
        obligadoContabilidad = 'SI'
        if company.partner_id.property_account_position_id.name == u'Persona natural no obligada a llevar contabilidad':
            obligadoContabilidad = 'NO'
        try:
            identification_type= utils.tipoIdentificacion[partner.l10n_latam_identification_type_id.display_name] if partner.l10n_latam_identification_type_id else '08'
        except:
            identification_type='08'
            
        infoFactura = {
            'fechaEmision': fix_date(invoice.invoice_date),
            'dirEstablecimiento': "{} {}".format(company.street, company.street2),
            'obligadoContabilidad': obligadoContabilidad,
            'tipoIdentificacionComprador': identification_type,  
            'razonSocialComprador': partner.name,
            'nombreComercial': company.tradename,
            'identificacionComprador': partner.vat,
            'totalSinImpuestos': '%.2f' % (invoice.amount_untaxed),
            'totalDescuento': '0.00',
            'propina': '0.00',
            'importeTotal': '{:.2f}'.format(invoice.amount_paid),
            'moneda': 'DOLAR',
            'formaPago': invoice.epayment_id.code,
            'valorRetIva': 0.00, #'{:.2f}'.format(invoice.taxed_ret_vatsrv + invoice.taxed_ret_vatb),  
            'valorRetRenta':0.00, #'{:.2f}'.format(invoice.amount_tax_ret_ir),
            'direccionProveedor': "{} {}".format(partner.street, partner.street2)
        }
        
        if company.special_taxpayer == 'SI':
            infoFactura.update({'contribuyenteEspecial': company.company_registry})

        totalConImpuestos = []
        taxes = self.env['account.tax'].search([('type_tax_use', '=', 'sale'),('company_id', '=', company.id)])
        totalRetIva = 0.00
        totalRetRenta = 0.00
        for mov in invoice.line_ids:
            temp_tax = taxes.filtered(lambda x: x.name == mov.name)
            if temp_tax and temp_tax.tax_group_id.l10n_ec_type in ['vat12', 'vat0', 'ice']:
                totalImpuesto = {
                            'codigo': utils.tabla17[temp_tax.tax_group_id.l10n_ec_type],
                            'codigoPorcentaje': utils.tabla18[str(int(temp_tax.real_amount))],
                            'baseImponible': mov.tax_base_amount,
                            'tarifa': int(temp_tax.real_amount),
                            'valor': abs(mov.amount_currency)
                        }
                totalConImpuestos.append(totalImpuesto)
            if temp_tax and temp_tax.tax_group_id.l10n_ec_type in ['withhold_vat']:
                totalRetIva += abs(mov.amount_currency)
            
            if temp_tax and temp_tax.tax_group_id.l10n_ec_type in ['withhold_income_tax','outflows_tax']:
                totalRetRenta += abs(mov.amount_currency)
        
        infoFactura['valorRetIva'] = totalRetIva
        infoFactura['valorRetRenta'] = totalRetRenta


        infoFactura.update({'totalConImpuestos': totalConImpuestos})
        
        if self.move_type == 'out_refund':
            """
            Estos datos faltan
            """
            notacredito = {
                'codDocModificado': 'factuta.auth_inv_id.type_id.code',
                'numDocModificado': 'inv_number',
                'motivo': 'self.comentario',
                'fechaEmisionDocSustento': 'fix_date(factuta.date_invoice',
                'valorModificacion': self.amount_total
            }
            

            infoFactura.update(notacredito)
        return infoFactura
        # except Exception as e:
        #     if error_mesagge != '':
        #         raise UserError(error_mesagge)
        #     raise UserError(e.message)

    def _detalles(self, invoice):
        """
        Retorna el tetalle de la factura
        :param invoice:
        :return:
        """
        detalles = []
        def fix_chars(code):
            special = [
                [u'%', ' '],
                [u'º', ' '],
                [u'Ñ', 'N'],
                [u'ñ', 'n']
            ]
            for f, r in special:
                code = code.replace(f, r)
            return code
        
        for line in invoice.invoice_line_ids:
            codigoPrincipal = line.product_id and \
                              line.product_id.default_code and \
                              fix_chars(line.product_id.default_code) or '001'
            priced = line.price_unit * (1 - (line.discount or 0.00) / 100.0)
            discount = (line.price_unit - priced) * line.quantity
            descripcion = line.name.strip()
            
            detalle = {
                'codigoPrincipal': codigoPrincipal,
                'descripcion': fix_chars(descripcion),
                'cantidad': '%.2f' % (line.quantity),
                'precioUnitario': '%.2f' % (line.price_unit),
                'descuento': '%.2f' % discount,
                'precioTotalSinImpuesto': '%.2f' % (line.price_subtotal)
            }
        
            totalConImpuestos = []
            taxes = self.env['account.tax'].search([('type_tax_use', '=', 'sale'),('company_id', '=', invoice.company_id.id)])
            for mov in invoice.line_ids:
                temp_tax = taxes.filtered(lambda x: x.name == mov.name)
                if temp_tax and temp_tax.tax_group_id.l10n_ec_type in ['vat12', 'vat0', 'ice']:
                    totalImpuesto = {
                                'codigo': utils.tabla17[temp_tax.tax_group_id.l10n_ec_type],
                                'codigoPorcentaje': utils.tabla18[str(int(temp_tax.real_amount))],
                                'baseImponible': mov.tax_base_amount,
                                'tarifa': int(temp_tax.real_amount),
                                'valor': abs(mov.amount_currency)
                            }
                    totalConImpuestos.append(totalImpuesto)

      
        
            detalle.update({'impuestos': totalConImpuestos})
            detalles.append(detalle)

        return {'detalles': detalles}

    def _detalles_refund(self, invoice):
        """
        Detalle de la nota de credito
        :param invoice:
        :return:
        """

        refunds = self.env['account.invoice'].search(
            [('company_id', '=', self.env.user.company_id.id), ('id', '=', invoice.id)])
        refund = {
            'codDocReembolso': '',
            'totalComprobantesReembolso': 0.00,
            'totalBaseImponibleReembolso': 0.00,
            'totalImpuestoReembolso': 0.00
        }
        detail = {}
        for rf in refunds:
            refund['codDocReembolso'] = rf.sustento_id.code
            refund['totalComprobantesReembolso'] += rf.amount_pay
            refund['totalBaseImponibleReembolso'] += rf.amount_untaxed
            refund['totalImpuestoReembolso'] += rf.amount_tax

            detail['tipoIdentificacionProveedorReembolso'] = utils.tipoIdentificacion[rf.partner_id.type_identifier]
            detail['identificacionProveedorReembolso'] = rf.partner_id.identifier
            detail['codPaisPagoProveedorReembolso'] = rf.partner_id.country_id.code
            detail['tipoProveedorReembolso'] = utils.getTabla26(rf.partner_id.property_account_position_id.id)
            detail['codDocReembolso'] = self.env.user.company_id.env_service
            detail['estabDocReembolso'] = rf.auth_inv_id.serie_entidad
            detail['ptoEmiDocReembolso'] = rf.auth_inv_id.serie_emision
            detail['secuencialDocReembolso'] = rf.reference
            detail['fechaEmisionDocReembolso'] = rf.date_invoice
            detail['numeroautorizacionDocReemb'] = rf.auth_number

            impuestos = []
            for line in rf.invoice_line_ids:
                for tax_line in line.invoice_line_tax_ids:
                    if tax_line.tax_group_id.code in ['vat', 'vat0', 'ice']:
                        impuesto = {
                            'codigo': utils.tabla17[tax_line.tax_group_id.code],
                            'codigoPorcentaje': utils.tabla18[tax_line.percent_report],  
                            'tarifa': tax_line.percent_report,
                            'baseImponible': '{:.2f}'.format(line.price_subtotal),
                            'valor': '{:.2f}'.format(line.price_subtotal *
                                                     tax_line.amount / 100)
                        }

                        impuestos.append(impuesto)

            detail.update({'impuestos': impuestos})

            refund.update({'detail': detail})
        return refund

    def _compute_discount(self, detalles):
        """
        Calcula el descuento
        :param detalles:
        :return:
        """
        total = sum([float(det['descuento']) for det in detalles['detalles']])
        return {'totalDescuento': total}

    def render_document(self, invoice, access_key, emission_code):
        """
        Crea el xml de los documentos
        :param invoice:
        :param access_key:
        :param emission_code:
        :return:
        """
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        einvoice_tmpl = env.get_template(self.TEMPLATES[self.move_type])
        data = {}

        data.update(self._info_tributaria(invoice, access_key, emission_code))
        data.update(self._info_factura(invoice))
        detalles = self._detalles(invoice)
        data.update(detalles)
        data.update(self._compute_discount(detalles))
        contact_address = "{}, {}, {}".format(invoice.partner_id.street, invoice.partner_id.street2,invoice.partner_id.city)
        data.update({'direccionCliente': contact_address})
        email = invoice.partner_id.email
        data.update({'emailCliente': email})
        data.update({'telefono': invoice.partner_id.phone})
        data.update({'observaciones': '-'})
        # data.update({'observaciones': invoice.comentario or '-'})

        try:
            terminos_pago = 30 *(invoice.invoice_payment_term_id.line_ids[0].months) + invoice.invoice_payment_term_id.line_ids[0].days
        except:
            terminos_pago = 0
        data.update({'terminos_pago': terminos_pago})
        # if invoice.company_id.agente_retencion =='SI':
        #     data.update({'agenteRetencion': invoice.partner_id.phone})

        if invoice.move_type == 'liq_purchase':
            data.update({'liq_purchase': self._detalles_refund(invoice)})

        einvoice = einvoice_tmpl.render(data)

        return einvoice

    def render_authorized_einvoice(self, autorizacion):
        """
        renderea los datos de la autorizacion
        :param autorizacion:
        :return:
        """
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        einvoice_tmpl = env.get_template('authorized_einvoice.xml')
        auth_xml = {
            'estado': autorizacion.estado,
            'numeroAutorizacion': autorizacion.numeroAutorizacion,
            'ambiente': autorizacion.ambiente,
            'fechaAutorizacion': str(autorizacion.fechaAutorizacion.strftime("%d/%m/%Y %H:%M:%S")),  
            'comprobante': autorizacion.comprobante
        }
        auth_invoice = einvoice_tmpl.render(auth_xml)
        return auth_invoice

    
    def action_generate_einvoice(self):
        """
        Genera la factura a enviar
        :return:
        """
        if self.move_type not in ['out_invoice', 'out_refund', 'liq_purchase']:
            return
        if self.off_accounting:
            raise UserError(u'La factura no se puede enviar porque está marcada como fuera de contabilidad')
        try:
            for obj in self:
                if obj.move_type not in ['out_invoice', 'out_refund', 'liq_purchase']:
                    continue
                # self.check_date(obj.invoice_date)
                # self.check_before_sent()
                if not self.partner_id.vat:
                    raise UserError(u'El cliente no ha especificado la identificación')
                access_key, emission_code = self._get_codes(name='account.move')
                einvoice = self.render_document(obj, access_key, emission_code)
                inv_xml = DocumentXML(einvoice, obj.move_type)
                inv_xml.validate_xml()

                xades = Xades()
                file_pk12 = obj.company_id.electronic_signature
                password = obj.company_id.password_electronic_signature
                xades_error, signed_document = xades.sign(einvoice, file_pk12, password)
                obj.authorization_number = access_key
                logging.info('Factura Error ' + str(xades_error))
                if xades_error:
                    error_msg = signed_document
                    raise UserError(error_msg)

                ok, estado, errores  = inv_xml.send_receipt(signed_document)
                logging.info('Factura Sri ' + estado)
                self.authorization_state = estado

                if obj.company_id.env_service == '1':
                    obj.environment = 'PRUEBAS'
                else:
                    obj.environment = 'PRODUCCION'

                if not ok:
                    error_msg = errores
                    return False, errores
                else:
                    obj.authorization_sri = True
                
        except Exception as e:
            self._logger.Error('Error al generar la factura electrónica', e.args[0])
            raise UserError(U'Error de conección')

    
    def invoice_print(self):
        """
        Imprime la factura
        :return:
        """
        return self.env['report'].get_action(
            self,
            'l10n_ec_einvoice.report_einvoice'
        )
