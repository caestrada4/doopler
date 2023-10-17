from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError

class ProductTelas(models.Model):
    _inherit= 'product.template'
    colorTela=fields.Many2one('product.color.catalogo',string="Colores")

    visilloTela=fields.Many2one('product.visillo.catalogo',string='Visillo')
    texturaTela=fields.Many2one('product.textura.catalogo',string='Textura')
    composicionTela=fields.Many2one('product.composicion.catalogo',string='Composicion')
    pesoTela=fields.Float(string='Peso')
    presentacionTela=fields.Many2one('product.presentacion.catalogo',string='Presentacion')
    anchorolloTela=fields.Float(string='Ancho de Rollo')
    anchofranjaTela=fields.Float(string='Ancho de franja')
    aperturaTela=fields.Float(string='Apertura')
    umrollo=fields.Many2one('product.template',related='uom_id',string='Unidad de medida')
    umfranja=fields.Many2one('product.unidad.catalogo',string='Unidad de medida')

class ProductPerfileria(models.Model):
    _inherit= 'product.template'
    colorPerfileria=fields.Many2one('product.color.catalogo',string="Colores")
    pestaniaPerfileria=fields.Boolean(string="Pestañas",default=False)
    ranuraPerfileria=fields.Boolean(string='Ranura',default=False)
    longitudPerfileria=fields.Float(string='Longitud')
    diametroPerfileria=fields.Float(string='Diametro')
    medidaRanuraPerfileria=fields.Float(string='Medida Ranura')
    umlongitud=fields.Many2one('product.unidad.catalogo',string='Unidad de medida')
    umdiametro=fields.Many2one('product.unidad.catalogo',string='Unidad de medida')


class ProductAccesorios(models.Model):
    _inherit= 'product.template'
    colorAccesorios=fields.Many2one('product.color.catalogo',string="Colores")
    mandoAccesorios=fields.Many2one('product.mando.catalogo',string="Mandos")
    logoAccesorios=fields.Boolean(string="Logos",default=False)
    diametroAccesorios=fields.Float(string='Diametro')
    umdiametroA=fields.Many2one('product.unidad.catalogo',string='Unidad de medida')



class CatalogoColores(models.Model):
    _name= 'product.color.catalogo'
    _description = 'Colores'
    _rec_name = 'colorTel'
    colorTel = fields.Char('Colores', required=True, unique=True, ondelete='restrict')
    product_ids = fields.One2many('product.template','colorTela', string='Subclases')


    @api.onchange('colorTel')
    def set_caps(self):
        if self.colorTel:
            self.colorTel = str(self.colorTel).upper()
            # Consulta la base de datos para verificar si el valor del campo ya existe
            if self.search([('colorTel', '=', self.colorTel)]):
                # Si el valor ya existe, lanza una excepción con un mensaje personalizado
                raise ValidationError('El color '+self.colorTel+' ya está registrado.')
        else:
            self.colorTel = ''

    def unlink(self):
        for record in self:
            # Verifica si el color está siendo utilizado por algún producto
            if record.product_ids:
                raise UserError('No se puede eliminar el color "{}" porque está siendo utilizado por uno o más productos.'.format(record.colorTel))
        # Llama al método padre para continuar con la eliminación
        return super(CatalogoColores, self).unlink()


class CatalogoVisillo(models.Model):
    _name= 'product.visillo.catalogo'
    _description = 'Visillo'
    _rec_name = 'visillo'
    visillo = fields.Char('Visillos', required=True,unique=True, ondelete='restrict')
    product_ids = fields.One2many('product.template','visilloTela', string='Subclases')

    
    @api.onchange('visillo')
    def set_caps(self):        
        if self.visillo:
            self.visillo=str(self.visillo).upper()
            if self.search([('visillo', '=', self.visillo)]):
                # Si el valor ya existe, lanza una excepción con un mensaje personalizado
                raise ValidationError('El visillo '+self.visillo+' ya está registrado.')
        else:
            self.visillo=''
    def unlink(self):
        for record in self:
            # Verifica si el color está siendo utilizado por algún producto
            if record.product_ids:
                raise UserError('No se puede eliminar el visillo "{}" porque está siendo utilizado por uno o más productos.'.format(record.visillo))
        # Llama al método padre para continuar con la eliminación
        return super(CatalogoVisillo, self).unlink()

class CatalogoTextura(models.Model):
    _name= 'product.textura.catalogo'
    _description = 'Texturas'
    _rec_name = 'textura'
    textura = fields.Char('Texturas', required=True,unique=True, ondelete='restrict')
    product_ids = fields.One2many('product.template','texturaTela', string='Subclases')

    @api.onchange('textura')
    def set_caps(self):        
        if self.textura:
            self.textura=str(self.textura).upper()
            if self.search([('textura', '=', self.textura)]):
                # Si el valor ya existe, lanza una excepción con un mensaje personalizado
                raise ValidationError('La textura '+self.textura+' ya está registrado.')
        else:
            self.textura=''
    def unlink(self):
        for record in self:
            # Verifica si el color está siendo utilizado por algún producto
            if record.product_ids:
                raise UserError('No se puede eliminar la textura "{}" porque está siendo utilizado por uno o más productos.'.format(record.textura))
        # Llama al método padre para continuar con la eliminación
        return super(CatalogoTextura, self).unlink()


class CatalogoPresentacion(models.Model):
    _name= 'product.presentacion.catalogo'
    _description = 'Presentaciones'
    _rec_name = 'presentacion'
    presentacion = fields.Char('Presentaciones', required=True,unique=True, ondelete='restrict')
    product_ids = fields.One2many('product.template','presentacionTela', string='Subclases')

    @api.onchange('presentacion')
    def set_caps(self):        
        if self.presentacion:
            self.presentacion=str(self.presentacion).upper()
            if self.search([('presentacion', '=', self.presentacion)]):
                # Si el valor ya existe, lanza una excepción con un mensaje personalizado
                raise ValidationError('La presentacion '+self.presentacion+' ya está registrado.')
        else:
            self.presentacion=''
    def unlink(self):
        for record in self:
            # Verifica si el color está siendo utilizado por algún producto
            if record.product_ids:
                raise UserError('No se puede eliminar la presentación "{}" porque está siendo utilizado por uno o más productos.'.format(record.presentacion))
        # Llama al método padre para continuar con la eliminación
        return super(CatalogoPresentacion, self).unlink()
        



class CatalogoMando(models.Model):
    _name= 'product.mando.catalogo'
    _description = 'Mandos'
    _rec_name = 'mando'
    mando = fields.Char('Mandos', required=True,unique=True, ondelete='restrict')
    product_ids = fields.One2many('product.template','mandoAccesorios', string='Subclases')

    @api.onchange('mando')
    def set_caps(self):        
        if self.mando:
            self.mando=str(self.mando).upper()
            if self.search([('mando', '=', self.mando)]):
                # Si el valor ya existe, lanza una excepción con un mensaje personalizado
                raise ValidationError('El mando '+self.mando+' ya está registrado.')
        else:
            self.mando=''

    def unlink(self):
        for record in self:
            # Verifica si el color está siendo utilizado por algún producto
            if record.product_ids:
                raise UserError('No se puede eliminar el mando "{}" porque está siendo utilizado por uno o más productos.'.format(record.mando))
        # Llama al método padre para continuar con la eliminación
        return super(CatalogoMando, self).unlink()



class CatalogoComposicion(models.Model):
    _name= 'product.composicion.catalogo'
    _description = 'Composiciones'
    _rec_name = 'composicion'
    composicion = fields.Char('Composiciones', required=True,unique=True, ondelete='restrict')
    product_ids = fields.One2many('product.template','composicionTela', string='Subclases')

    @api.onchange('composicion')
    def set_caps(self):        
        if self.composicion:
            self.composicion=str(self.composicion).upper()
            if self.search([('composicion', '=', self.composicion)]):
                # Si el valor ya existe, lanza una excepción con un mensaje personalizado
                raise ValidationError('La composicion '+self.composicion+' ya está registrado.')
        else:
            self.composicion=''
    def unlink(self):
        for record in self:
            # Verifica si el color está siendo utilizado por algún producto
            if record.product_ids:
                raise UserError('No se puede eliminar el mando "{}" porque está siendo utilizado por uno o más productos.'.format(record.composicion))
        # Llama al método padre para continuar con la eliminación
        return super(CatalogoComposicion, self).unlink()
