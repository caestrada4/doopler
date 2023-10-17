odoo.define('l16n_ec_reconcile.ConciliacionBancarios', function (require) {
  'use strict'
  var AbstractAction = require('web.AbstractAction')

  var core = require('web.core')
  var list_cuentas = []
  var total = 0
  var QWeb = core.qweb
  var BanckConciliation = AbstractAction.extend({
    title: core._t('Conciliación Bancaria'),
    contentTemplate: 'l16n_ec_reconcile.BankConciliation',
    events: {
      'click .btn-conciliar': 'startConciliacion',
      'click .line-conciliacion': 'moveLineClickHandler',
      'click .line-conciliacion-unselect': 'moveLineUncheckHandler',
      'click .btn-send-conciliation': 'enviarConciliacion',
      'click .js_automatic_reconciliation': 'conciliarTodo',
      'click .show_more_container': 'mostrarMas',
    },
    start: function () {
      var self = this
      self.listBanck()
    },

    listBanck: function () {
      return this._rpc({
        model: 'account.bank.reconcile',
        method: 'bancos',
        args: [],
      }).then(function (result) {
        var html = QWeb.render('l16n_ec_reconcile.BankList', { items: result })
        $('#id_select_bank').html(html)
      })
    },

    startConciliacion: function (e) {
      var cuenta = $('#id_banco').val()
      var limite = $('#id_limite').val()

      this._rpc({
        model: 'account.bank.reconcile',
        method: 'list_conciliacion',
        args: [cuenta, limite],
      }).then(function (result) {
        list_cuentas = result
        console.log('recul', result)
        var html = QWeb.render('ListCuentas', { items: result })
        $('#reconciliation_lines_container').html(html)
      })
    },

    mostrarMas: function () {
      var limite = $('#id_limite').val()
      $('#id_limite').val(parseFloat(limite) + 10)
      this.startConciliacion()
    },

    conciliarTodo: function () {
      var self = this
      var limite = $('#id_limite').val()
      var cuenta = $('#id_banco').val()
      self
        ._rpc({
          model: 'account.bank.reconcile',
          method: 'automatic_conciliacion',
          args: [limite, cuenta],
        })
        .then(function (result) {
          self.startConciliacion()
        })
    },
    moveLineClickHandler: function (e) {
      this.selectMoveLine(e.currentTarget)
    },
    selectMoveLine: function (mv_line) {
      var self = this
      var line_id = mv_line.dataset.lineid
      var cuenta_id = line_id.substring(0, line_id.indexOf('-'))
      total = 0
      $.each(list_cuentas.account, function (id, cuenta) {
        if (cuenta.id == cuenta_id) {
          $.each(cuenta.conciliar, function (index, line) {
            try {
              if (line.id == line_id) {
                total = parseFloat(line.debit) + parseFloat(line.credit)
                var total_cuenta = cuenta.total + total
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

      var html = QWeb.render('ListCuentas', { items: list_cuentas })
      $('#reconciliation_lines_container').html(html)
    },
    moveLineUncheckHandler: function (e) {
      this.unselectMoveLine(e.currentTarget)
    },

    unselectMoveLine: function (mv_line) {
      var line_id = mv_line.dataset.lineid

      var cuenta_id = line_id.substring(0, line_id.indexOf('-'))
      $.each(list_cuentas.account, function (id, cuenta) {
        if (cuenta.id == cuenta_id) {
          $.each(cuenta.select, function (index, line) {
            try {
              if (line.id == line_id) {
                cuenta.conciliar.push(line)
                cuenta.select.splice(index, 1)

                total = parseFloat(line.debit) + parseFloat(line.credit)
                var total_cuenta = cuenta.total - total
                total_cuenta = Math.round(total_cuenta * 100) / 100
                cuenta.total = total_cuenta
                return
              }
            } catch (e) {}
          })
        }
      })
      var html = QWeb.render('ListCuentas', { items: list_cuentas })
      $('#reconciliation_lines_container').html(html)
    },

    enviarConciliacionApi: function (data) {},
    enviarConciliacion: function (e) {
      var self = this
      var cuenta_id = e.currentTarget.dataset.lineid
      $.each(list_cuentas.account, function (id, cuenta) {
        if (cuenta.id == cuenta_id) {
          // this.enviarConciliacionApi(cuenta)
          self
            ._rpc({
              model: 'account.bank.reconcile',
              method: 'conciliar',
              args: [cuenta],
            })
            .then(function (result) {
              self.startConciliacion()
              return
            })
        }
      })
    },
  })
  core.action_registry.add('conciliacion_bancaria', BanckConciliation)
  return {
    BanckConciliation: BanckConciliation,
  }
})

// BankConciliation
