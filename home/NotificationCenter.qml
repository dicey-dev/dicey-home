pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import qs.Commons
import qs.Commons as Commons
import "NotificationModel.js" as Model

FocusScope {
  id: center
  property real feedHeight: Style.space(400)
  property bool unreadOnly: false
  property bool confirmingClear: false
  readonly property var store: NotificationStore
  readonly property var rows: unreadOnly ? center.store.rows.filter(function(row) { return center.store.isUnread(row) }) : center.store.rows
  readonly property color muted: Qt.tint(Commons.Color.menu.background, Util.alpha(Commons.Color.menu.text, 0.72))
  signal revealRequested(var control)
  implicitHeight: body.implicitHeight
  onRowsChanged: syncFeed()
  Component.onCompleted: syncFeed()
  function syncFeed() {
    if (!feed || !feedModel) return
    var atTop = feed.atYBeginning
    Model.sync(feedModel, rows)
    if (atTop) feed.positionViewAtBeginning()
  }
  function inspectFeed() {
    var index = -1
    for (var y = 1; y < feed.height && index < 0; y++) index = feed.indexAt(1, feed.contentY + y)
    var item = index >= 0 ? feed.itemAtIndex(index) : null
    return {count: feedModel.count, topKey: index >= 0 ? feedModel.get(index).key : "",
      offset: item ? feed.contentY - item.y : 0,
      currentKey: feed.currentIndex >= 0 && feed.currentIndex < feedModel.count ? feedModel.get(feed.currentIndex).key : ""}
  }
  ListModel { id: feedModel }
  function focusFeed() { allButton.forceActiveFocus() }
  function reset() { confirmingClear = false }
  function action(name) {
    if (name === "view") { focusFeed(); return "ok" }
    if (name === "read") return center.store.markRead()
    if (name === "requestClear") { confirmingClear = true; Qt.callLater(function() { cancelClear.forceActiveFocus() }); return "confirm" }
    if (name === "cancelClear") { confirmingClear = false; focusFeed(); return "ok" }
    if (name === "confirmClear") {
      if (!confirmingClear) return "unavailable"
      confirmingClear = false
      focusFeed()
      return center.store.run("clearHistory")
    }
    return ["dndOn", "dndOff", "replay", "dismissLatest", "openLatest"].indexOf(name) >= 0 ? center.store.run(name) : "unavailable"
  }
  Keys.onPressed: function(event) {
    if (event.key === Qt.Key_Escape && confirmingClear) { confirmingClear = false; allButton.forceActiveFocus(); event.accepted = true }
  }
  component CenterButton: HomeButton {
    onActiveFocusChanged: if (activeFocus) center.revealRequested(this)
  }
  Column {
    id: body
    width: parent.width
    spacing: Style.space(12)
    Column {
      width: parent.width
      spacing: Style.space(3)
      Text { text: "Notifications"; color: Commons.Color.menu.text; font.family: Style.font.menuFamily; font.pixelSize: Style.font.heading }
      Text { text: "01 / " + (center.store.ready ? center.store.unreadCount + " UNREAD" : "CONNECTING…") + (center.store.snapshot.dnd === true ? " · DND ON" : ""); color: center.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
    }
    Flow {
      width: parent.width
      spacing: Style.space(6)
      CenterButton { id: allButton; text: center.unreadOnly ? "Show all" : "Unread only"; onClicked: center.unreadOnly = !center.unreadOnly }
      CenterButton { text: "Mark all read"; enabled: center.store.ready && center.store.unreadCount > 0; onClicked: center.action("read") }
      CenterButton { text: center.store.snapshot.dnd === true ? "DND: on" : center.store.snapshot.dnd === false ? "DND: off" : "Set DND"; enabled: center.store.ready && !center.store.commandPending; Accessible.name: "Toggle do not disturb"; onClicked: center.action(center.store.snapshot.dnd === true ? "dndOff" : "dndOn") }
    }
    Rectangle {
      width: parent.width
      height: center.feedHeight
      radius: Math.min(Style.cornerRadius, Style.space(6))
      color: Util.alpha(Commons.Color.menu.text, 0.035)
      border.width: Style.spacing.hairline
      border.color: feed.activeFocus ? Commons.Color.accent : Util.alpha(Commons.Color.menu.text, 0.14)
      ListView {
        id: feed
        anchors.fill: parent
        anchors.margins: Style.space(12)
        clip: true
        model: feedModel
        activeFocusOnTab: true
        keyNavigationEnabled: true
        Accessible.name: "Notification feed"
        onActiveFocusChanged: if (activeFocus) center.revealRequested(this)
        Keys.onPressed: function(event) {
          if (event.key === Qt.Key_PageDown || event.key === Qt.Key_PageUp) {
            contentY = Math.max(originY, Math.min(originY + Math.max(0, contentHeight - height), contentY + (event.key === Qt.Key_PageDown ? 1 : -1) * height * 0.8))
            event.accepted = true
          }
        }
        spacing: Style.space(14)
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        delegate: Item {
          id: entry
          required property var model
          width: feed.width - Style.space(8)
          height: details.implicitHeight + Style.space(18)
          readonly property bool unread: center.store.isUnread(model)
          Rectangle { width: Style.space(2); height: parent.height - Style.space(8); color: entry.model.urgency === 2 ? Commons.Color.urgent : Commons.Color.accent; opacity: entry.unread ? 1 : 0.15 }
          Column {
            id: details
            x: Style.space(12)
            width: parent.width - x
            spacing: Style.space(5)
            Text { width: parent.width; text: (entry.unread ? "● " : "") + entry.model.app + (entry.model.urgency === 2 ? " · URGENT" : ""); textFormat: Text.PlainText; elide: Text.ElideRight; color: entry.model.urgency === 2 ? Commons.Color.urgent : center.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
            Text { width: parent.width; text: entry.model.summary; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: Commons.Color.menu.text; font.family: Style.font.menuFamily; font.pixelSize: Style.font.body; font.weight: entry.unread ? Font.DemiBold : Font.Normal }
            Text { width: parent.width; visible: text.length > 0; text: entry.model.body; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: center.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
            Text { width: parent.width; text: Qt.formatDateTime(new Date(entry.model.timestamp), "d MMM · HH:mm") + (entry.model.live ? " · LIVE TOAST" : " · RECENT"); color: center.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
          }
          Accessible.role: Accessible.StaticText
          Accessible.name: model.app + ": " + model.summary + ". " + model.body
        }
        Text {
          anchors.centerIn: parent
          width: parent.width - Style.space(20)
          visible: !center.rows.length
          text: !center.store.ready ? (center.store.snapshot.error || (!center.store.hostAvailable ? "Notification service unavailable.\nWaiting for Omarchy…" : "Connecting to notifications…")) : center.unreadOnly ? "You’re caught up.\nNo unread notifications." : "A little quiet.\nNew notifications will appear here."
          textFormat: Text.PlainText
          horizontalAlignment: Text.AlignHCenter
          wrapMode: Text.Wrap
          color: center.muted
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.body
        }
      }
    }
    Text {
      width: parent.width
      visible: !center.store.ready || center.store.snapshot.warning || center.store.commandError.length > 0
      text: center.store.snapshot.error || center.store.commandError || (!center.store.ready ? "Waiting for the notification reader and host service." : "Some snapshots were skipped or the feed was limited to the newest 256.")
      textFormat: Text.PlainText
      wrapMode: Text.Wrap
      color: Commons.Color.urgent
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.caption
    }
    Text { width: parent.width; text: "Toast controls act on the newest visible toast, not a selected history entry."; wrapMode: Text.Wrap; color: center.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
    Flow {
      width: parent.width
      spacing: Style.space(6)
      CenterButton { text: "Open latest toast ↗"; enabled: center.store.ready && !center.store.commandPending; onClicked: center.action("openLatest") }
      CenterButton { text: "Dismiss latest toast"; enabled: center.store.ready && !center.store.commandPending; onClicked: center.action("dismissLatest") }
      CenterButton { text: "Replay recent"; enabled: center.store.ready && !center.store.commandPending; onClicked: center.action("replay") }
      CenterButton { text: "Clear history…"; enabled: center.store.ready && center.store.rows.length > 0 && !center.store.commandPending; onClicked: center.action("requestClear") }
    }
    Column {
      width: parent.width
      visible: center.confirmingClear
      spacing: Style.space(6)
      Text { width: parent.width; text: "Permanently clear Omarchy’s shared recent history? Live toasts stay. This cannot be undone."; wrapMode: Text.Wrap; color: Commons.Color.menu.text; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
      Row {
        spacing: Style.space(8)
        CenterButton { id: cancelClear; text: "Cancel"; onClicked: center.action("cancelClear") }
        CenterButton { text: "Clear shared history"; enabled: !center.store.commandPending; onClicked: center.action("confirmClear") }
      }
    }
  }
}
