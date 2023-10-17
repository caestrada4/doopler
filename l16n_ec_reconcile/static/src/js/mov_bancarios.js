odoo.define('l16n_ec_reconcile.MovBancarios', function (require) {
  'use strict'
  var AbstractAction = require('web.AbstractAction')

  var core = require('web.core')
  // var hooks = require('web.hooks')
  var QWeb = core.qweb

  //var ajax = require('web.ajax')

  var BanckMove = AbstractAction.extend({
    title: core._t('Movimientos Bancarios'),
    contentTemplate: 'l16n_ec_reconcile.mov_bancarios',
    events: {
      'click .id_btn_buscar': 'actionBuscar',
      'click .id_btn_conciliar': 'actionConciliar',
      'click .btn_siquiente': 'actionSiquiente',
      'click .btn_anterior': 'actionAnterior',
      'click .btn-procesar-conciliacion': 'procesarConciliacion',
    },
    start: function () {
      var self = this
      self.listPartner()
      self.listAccount()
      //this.action = hooks.useService('action')
    },

    listPartner: function () {
      return this._rpc({
        model: 'bank.account.move',
        method: 'list_res_parther',
        args: [],
      }).then(function (result) {
        var html = QWeb.render('SelectPartner', { items: result })
        $('#id_div_clientes').html(html)
      })
    },
    listAccount: function () {
      return this._rpc({
        model: 'bank.account.move',
        method: 'list_account',
        args: [],
      }).then(function (result) {
        var html = QWeb.render('SelectAccount', { items: result })
        $('#id_select_account').html(html)
      })
    },
    actionBuscar: function () {
      var inicio = $('#id_inicio').val()

      var fecha_inicio = $('#id_fecha_desde').val()
      var fecha_hasta = $('#id_fecha_hasta').val()
      var no_documento = $('#id_nodocumento').val()
      var select = $('#id_select option:selected').val()
      var partner = $('#id_partner option:selected').val()
      var account = $('#id_cuentas option:selected').val()
      var valor = $('#id_valor').val()
      var estados = $('#id_estado option:selected').val()
      console.log('valor', valor)
      console.log('account', account)
      console.log('estado', estados)

      return this._rpc({
        model: 'bank.account.move',
        method: 'action_load_entries',
        args: [
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
      }).then(function (result) {
        var html = QWeb.render('TableResultLine', {
          items: result,
          init: inicio,
        })
        $('#id_table_result').html(html)
      })
    },
    actionConciliar: function (e) {
      console.log(e.currentTarget.id)
    },

    actionSiquiente: function () {
      var total = $('#id_inicio').val()
      total = parseInt(total) + 1
      $('#id_inicio').val(total)
      this.actionBuscar()
    },
    actionAnterior: function () {
      var total = $('#id_inicio').val()
      if (total > 0) {
        total = parseInt(total) - 1
        $('#id_inicio').val(total)
        this.actionBuscar()
      }
    },
    // conciliacion manual
    procesarConciliacion: function (e) {
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
        this.do_action(action)
      } else {
        return this._rpc({
          model: 'bank.account.move',
          method: 'conciliar',
          args: [id],
        }).then(function (result) {
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
  })
  core.action_registry.add('movimientos_bancarios', BanckMove)
  return {
    BanckMove: BanckMove,
  }
})
