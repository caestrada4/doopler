odoo.l16n_ec_reconcile = function (instance, local) {
  var _t = instance.web._t,
    _lt = instance.web._lt
  var QWeb = instance.web.qweb
  this.list_cuentas = {}

  local.HomePage = instance.Widget.extend({
    template: 'HomePage',
    start: function () {
      var self = this
      this.$('.js_automatic_reconciliation').click(function () {
        var limite = $('#id_limite').val()
        var cuenta = $('#id_banco').val()
        var model = new instance.web.Model('account.bank.reconcile')

        model
          .call('automatic_conciliacion', [limite, cuenta], {
            context: new instance.web.CompoundContext(),
          })
          .then(function (result) {
            return $.when(
              new local.CuentasDetails(self).appendTo(
                self.$('.reconciliation_lines_container'),
              ),
            )
          })
      })

      this.$('.btn-conciliar').click(function () {
        $('#id_limite').val(10)
        return $.when(
          new local.CuentasDetails(self).appendTo(
            self.$('.reconciliation_lines_container'),
          ),
        )
      })

      this.$('.show_more_container').click(function () {
        var limite = $('#id_limite').val()
        $('#id_limite').val(parseFloat(limite) + 10)
        return $.when(
          new local.CuentasDetails(self).appendTo(
            self.$('.reconciliation_lines_container'),
          ),
        )
      })

      return $.when(
        new local.BanksWidget(this).appendTo(
          this.$('.oe_conciliacion_homepage_left'),
        ),
      )
    },

    listLines: function (e) {
      var limite = $('#id_limite').val()
      $('#id_limite').val(parseFloat(limite) + 10)
      return $.when(
        new local.CuentasDetails(self).appendTo(
          self.$('.reconciliation_lines_container'),
        ),
      )
    },
  })

  local.BanksWidget = instance.Widget.extend({
    template: 'BanksWidget',
    start: function () {
      var self = this
      var model = new instance.web.Model('account.bank.reconcile')
      model
        .call('bancos', { context: new instance.web.CompoundContext() })
        .then(function (result) {
          self.$el.append(
            QWeb.render('l16n_ec_reconcile.BankList', { item: result }),
          )
        })
    },
  })

  local.CuentasDetails = instance.Widget.extend({
    template: 'CuentasDetails',
    events: {
      'click .line-conciliacion': 'moveLineClickHandler',
      'click .line-conciliacion-unselect': 'moveLineUncheckHandler',
      'click .btn-send-conciliation': 'enviarConciliacion',
    },
    start: function () {
      this.startConciliacion()
      this.$('.js_automatic_reconciliation').click(function () {
        console.log(self.list_cuentas)
      })
    },
    startConciliacion: function (e) {
      var self = this
      $('.oe_conciliacio_list1').html('')
      var cuenta = $('#id_banco').val()
      var limite = $('#id_limite').val()
      var model = new instance.web.Model('account.bank.reconcile')

      model
        .call('list_conciliacion', [cuenta, limite], {
          context: new instance.web.CompoundContext(),
        })
        .then(function (result) {
          self.list_cuentas = result
          self.$el.append(QWeb.render('ListCuentas', { items: result }))
        })
    },
    enviarConciliacion: function (e) {
      var self = this
      cuenta_id = e.currentTarget.dataset.lineid
      $.each(self.list_cuentas.account, function (id, cuenta) {
        if (cuenta.id == cuenta_id) {
          self.enviarConciliacionApi(cuenta)
        }
      })
    },

    enviarConciliacionApi: function (data) {
      var self = this
      var model = new instance.web.Model('account.bank.reconcile')
      model
        .call('conciliar', [data], {
          context: new instance.web.CompoundContext(),
        })
        .then(function (result) {
          self.startConciliacion()
        })
    },

    moveLineClickHandler: function (e) {
      var self = this
      self.selectMoveLine(e.currentTarget)
    },
    selectMoveLine: function (mv_line) {
      var self = this
      var line_id = mv_line.dataset.lineid
      var cuenta_id = line_id.substring(0, line_id.indexOf('-'))
      total = 0
      $.each(self.list_cuentas.account, function (id, cuenta) {
        if (cuenta.id == cuenta_id) {
          $.each(cuenta.conciliar, function (index, line) {
            try {
              if (line.id == line_id) {
                total = parseFloat(line.debit) + parseFloat(line.credit)
                total_cuenta = cuenta.total + total
                total_cuenta = Math.round(total_cuenta * 100) / 100
                cuenta.total = total_cuenta
                cuenta.select.push(line)
                cuenta.conciliar.splice(index, 1)
                return
              }
            } catch (e) {}
          })
        }
      })
      $('.oe_conciliacio_list1').html('')
      self.$el.append(QWeb.render('ListCuentas', { items: self.list_cuentas }))
    },

    moveLineUncheckHandler: function (e) {
      var self = this
      self.unselectMoveLine(e.currentTarget)
    },

    unselectMoveLine: function (mv_line) {
      var self = this
      var line_id = mv_line.dataset.lineid

      var cuenta_id = line_id.substring(0, line_id.indexOf('-'))
      $.each(self.list_cuentas.account, function (id, cuenta) {
        if (cuenta.id == cuenta_id) {
          $.each(cuenta.select, function (index, line) {
            try {
              if (line.id == line_id) {
                cuenta.conciliar.push(line)
                cuenta.select.splice(index, 1)

                total = parseFloat(line.debit) + parseFloat(line.credit)
                total_cuenta = cuenta.total - total
                total_cuenta = Math.round(total_cuenta * 100) / 100
                cuenta.total = total_cuenta
                //cuenta.total -= parseFloat(line.debit) + parseFloat(line.credit);
                return
              }
            } catch (e) {}
          })
        }
      })

      $('.oe_conciliacio_list1').html('')
      self.$el.append(QWeb.render('ListCuentas', { items: self.list_cuentas }))
    },
  })

  instance.web.client_actions.add(
    'conciliacion.bancaria',
    'instance.l16n_ec_reconcile.HomePage',
  )

  local.MovimientoBancarios = instance.Widget.extend({
    template: 'MovimientoBancarios',
    events: {
      'click .btn-procesar-conciliacion': 'procesarConciliacion',
      'click .btn_siquiente': 'actionSiquiente',
      'click .btn_anterior': 'actionAnterior',
    },
    start: function () {
      $('#id_inicio').val(0)
      self = this
      this.$('#id_btn_movimientos_bancos').click(function () {
        $('#id_inicio').val(0)
        return $.when(
          new local.BancosDetails(self).appendTo(self.$('.list_bancos')),
        )
      })

      this.$('#id_btn_movimientos_bancos_export').click(function () {
        var fecha_inicio = $('#id_fecha_desde').val()
        var fecha_hasta = $('#id_fecha_hasta').val()
        var no_documento = $('#id_nodocumento').val()
        var select = $('#id_select option:selected').val()
        var valor = $('#id_valor').val()
        var partner = $('#id_partner option:selected').val()
        var account = $('#id_cuentas option:selected').val()
        var estados = $('#id_estado option:selected').val()

        var model = new instance.web.Model('bank.account.move')

        model
          .call(
            'acction_export',
            [
              fecha_inicio,
              fecha_hasta,
              no_documento,
              select,
              valor,
              partner,
              account,
              estados,
            ],
            { context: new instance.web.CompoundContext() },
          )
          .then(function (result) {
            var action = {
              type: 'ir.actions.act_window',
              res_model: 'excel.descargar',
              view_type: 'form',
              view_mode: 'form',
              res_id: result.res_id,
              views: [[false, 'form']],
              target: 'new',
              //context: new instance.web.CompoundContext()
            }

            self.do_action(action)

            // self.$el.append(QWeb.render('ListBank', {items: result}));
          })
      })
      return $.when(
        new local.PartnerWidget(this).appendTo(this.$('.clientes')),
        new local.AccountWidget(this).appendTo(this.$('.cuentas')),
      )
    },

    procesarConciliacion: function (e) {
      var self = this
      var id = e.currentTarget.id
      var estado = $('#td_' + id).html()
      estado = estado.trim()
      if (estado == 'No') {
        var action = {
          type: 'ir.actions.act_window',
          res_model: 'conciliacion.manual',
          view_type: 'form',
          view_mode: 'form',
          views: [[false, 'form']],
          target: 'new',
          context: {
            move_id: id,
          },
        }
        self.do_action(action)
      } else {
        var model = new instance.web.Model('bank.account.move')
        model
          .call('conciliar', [id], {
            context: new instance.web.CompoundContext(),
          })
          .then(function (result) {
            if (result) {
              $('#' + id).removeClass('btn btn-primary')
              $('#' + id).addClass('btn btn-secondary')
              $('#' + id).html('Romper')
              $('#td_' + id).html('Si')
            } else {
              $('#' + id).removeClass('btn btn-secondary')
              $('#' + id).addClass('btn btn-primary')
              $('#' + id).html('Conciliar')
              $('#td_' + id).html('No')
            }
          })
      }
    },

    actionSiquiente: function () {
      var total = $('#id_inicio').val()
      total = parseInt(total) + 1
      $('#id_inicio').val(total)
      return $.when(
        new local.BancosDetails(self).appendTo(self.$('.list_bancos')),
      )
    },
    actionAnterior: function () {
      var total = $('#id_inicio').val()
      if (total > 0) {
        total = parseInt(total) - 1
        $('#id_inicio').val(total)
        return $.when(
          new local.BancosDetails(self).appendTo(self.$('.list_bancos')),
        )
      }
    },
  })

  local.PartnerWidget = instance.Widget.extend({
    template: 'PartnerWidget',
    start: function () {
      var self = this
      var model = new instance.web.Model('bank.account.move')
      model
        .call('list_res_parther', {
          context: new instance.web.CompoundContext(),
        })
        .then(function (result) {
          self.$el.append(QWeb.render('SelectPartner', { item: result }))
        })
    },
  })

  local.AccountWidget = instance.Widget.extend({
    template: 'AccountWidget',
    start: function () {
      var self = this
      var model = new instance.web.Model('bank.account.move')
      model
        .call('list_account', { context: new instance.web.CompoundContext() })
        .then(function (result) {
          self.$el.append(QWeb.render('SelectAccount', { item: result }))
        })
    },
  })

  local.BancosDetails = instance.Widget.extend({
    template: 'BancosDetails',
    start: function () {
      var self = this
      this.startListBnk()
    },
    startListBnk: function (e) {
      var inicio = $('#id_inicio').val()

      var fecha_inicio = $('#id_fecha_desde').val()
      var fecha_hasta = $('#id_fecha_hasta').val()
      var no_documento = $('#id_nodocumento').val()
      var select = $('#id_select option:selected').val()
      var partner = $('#id_partner option:selected').val()
      var account = $('#id_cuentas option:selected').val()
      var valor = $('#id_valor').val()
      var estados = $('#id_estado option:selected').val()
      var model = new instance.web.Model('bank.account.move')
      model
        .call(
          'action_load_entries',
          [
            fecha_inicio,
            fecha_hasta,
            no_documento,
            select,
            valor,
            partner,
            account,
            estados,
            inicio,
          ],
          { context: new instance.web.CompoundContext() },
        )
        .then(function (result) {
          $('.borrar-bank').html('')
          self.$el.append(
            QWeb.render('ListBank', { items: result, init: inicio }),
          )
        })
    },
  })

  instance.web.client_actions.add(
    'movimientos.bancarios',
    'instance.l16n_ec_reconcile.MovimientoBancarios',
  )
}
