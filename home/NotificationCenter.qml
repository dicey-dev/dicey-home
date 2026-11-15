pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import qs.Commons
import qs.Commons as Commons
import "NotificationModel.js" as Model

FocusScope {
  id: center
  property real feedHeight: Style.space(400)
  readonly property var store: NotificationStore
  readonly property var rows: center.store.rows
  readonly property int groupCount: Object.keys(center.store.groups).length
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
  function currentKey() { return feed.currentIndex >= 0 && feed.currentIndex < feedModel.count ? feedModel.get(feed.currentIndex).key : "" }
  function inspectFeed() {
    var index = -1
    for (var y = 1; y < feed.height && index < 0; y++) index = feed.indexAt(1, feed.contentY + y)
    var item = index >= 0 ? feed.itemAtIndex(index) : null
    return {count: feedModel.count, topKey: index >= 0 ? feedModel.get(index).key : "",
      offset: item ? feed.contentY - item.y : 0, currentKey: currentKey()}
  }
  ListModel { id: feedModel }
  function focusFeed() { if (feedModel.count) feed.forceActiveFocus(); else dndButton.forceActiveFocus() }
  function action(name) {
    if (name === "view") { focusFeed(); return "ok" }
    if (name === "clearAll") return center.store.removeAll()
    if (name.indexOf("remove:") === 0) return center.store.removeOne(name.slice(7))
    if (name.indexOf("clearGroup:") === 0) return center.store.removeGroup(name.slice(11))
    return ["dndOn", "dndOff"].indexOf(name) >= 0 ? center.store.run(name) : "unavailable"
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
      Text {
        text: "01 / " + (!center.store.ready ? "CONNECTING…" : center.rows.length ? center.rows.length + " FROM " + center.groupCount + (center.groupCount === 1 ? " SOURCE" : " SOURCES") : "ALL CLEAR") + (center.store.dnd === true ? " · DND ON" : "")
        color: center.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption
      }
    }
    Flow {
      width: parent.width
      spacing: Style.space(6)
      CenterButton { id: dndButton; text: center.store.dnd === true ? "DND: on" : center.store.dnd === false ? "DND: off" : "Set DND"; enabled: center.store.ready && !center.store.commandPending; Accessible.name: "Toggle do not disturb"; onClicked: center.action(center.store.dnd === true ? "dndOff" : "dndOn") }
      CenterButton { text: "Clear all"; enabled: center.store.ready && center.rows.length > 0; Accessible.name: "Remove all notifications from this list"; onClicked: center.action("clearAll") }
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
        Accessible.name: "Notifications, grouped by source"
        onActiveFocusChanged: if (activeFocus) center.revealRequested(this)
        Keys.onPressed: function(event) {
          if (event.key === Qt.Key_PageDown || event.key === Qt.Key_PageUp) {
            contentY = Math.max(originY, Math.min(originY + Math.max(0, contentHeight - height), contentY + (event.key === Qt.Key_PageDown ? 1 : -1) * height * 0.8))
            event.accepted = true
          } else if (event.key === Qt.Key_Delete && currentIndex >= 0 && currentIndex < feedModel.count) {
            var row = feedModel.get(currentIndex)
            center.action(event.modifiers & Qt.ShiftModifier ? "clearGroup:" + row.group : "remove:" + row.key)
            event.accepted = true
          }
        }
        spacing: Style.space(6)
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        section.property: "group"
        section.criteria: ViewSection.FullString
        // The current group's header stays pinned while reading a long group.
        section.labelPositioning: ViewSection.InlineLabels | ViewSection.CurrentLabelAtStart
        section.delegate: Rectangle {
          id: header
          required property string section
          readonly property var info: center.store.groups[section]
          width: feed.width - Style.space(8)
          height: headerRow.implicitHeight + Style.space(14)
          z: 2
          color: Qt.tint(Commons.Color.menu.background, Util.alpha(Commons.Color.menu.text, 0.035))
          Row {
            id: headerRow
            y: Style.space(8)
            width: parent.width
            spacing: Style.space(8)
            Column {
              width: parent.width - clearGroup.width - parent.spacing
              anchors.verticalCenter: parent.verticalCenter
              spacing: Style.space(1)
              Text { width: parent.width; text: header.info ? header.info.label + "  " + header.info.count : ""; textFormat: Text.PlainText; elide: Text.ElideRight; color: Commons.Color.menu.text; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption; font.weight: Font.DemiBold }
              Text { width: parent.width; visible: text.length > 0; text: Model.caption(header.info ? Object.assign({id: header.section}, header.info) : null).toUpperCase(); textFormat: Text.PlainText; elide: Text.ElideRight; color: center.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
            }
            CenterButton { id: clearGroup; text: "Clear"; implicitHeight: Style.space(26); Accessible.name: "Remove all notifications from " + (header.info ? header.info.label : "this source"); onClicked: { feed.forceActiveFocus(); center.action("clearGroup:" + header.section); if (!feedModel.count) center.focusFeed() } }
          }
        }
        delegate: Item {
          id: entry
          required property var model
          required property int index
          width: feed.width - Style.space(8)
          height: details.implicitHeight + Style.space(14)
          readonly property var group: center.store.groups[entry.model.group]
          Rectangle { anchors.fill: parent; radius: Math.min(Style.cornerRadius, Style.space(4)); color: Util.alpha(Commons.Color.menu.text, 0.06); visible: feed.activeFocus && entry.ListView.isCurrentItem }
          Rectangle { y: Style.space(4); width: Style.space(2); height: parent.height - Style.space(8); color: entry.model.urgency === 2 ? Commons.Color.urgent : Commons.Color.accent; opacity: entry.model.urgency === 2 ? 1 : 0.35 }
          Column {
            id: details
            x: Style.space(12)
            y: Style.space(7)
            width: parent.width - x - remove.width - Style.space(8)
            spacing: Style.space(4)
            Text { width: parent.width; text: entry.model.summary; textFormat: Text.PlainText; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight; color: Commons.Color.menu.text; font.family: Style.font.menuFamily; font.pixelSize: Style.font.body }
            Text { width: parent.width; visible: text.length > 0; text: entry.model.body; textFormat: Text.PlainText; wrapMode: Text.Wrap; maximumLineCount: 4; elide: Text.ElideRight; color: center.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
            Text { width: parent.width; text: Qt.formatDateTime(new Date(entry.model.timestamp), "d MMM · HH:mm") + (entry.group && entry.group.browsers.length > 1 ? " · " + entry.model.browser.toUpperCase() : "") + (entry.model.urgency === 2 ? " · URGENT" : "") + (entry.model.live ? " · ON SCREEN" : ""); color: entry.model.urgency === 2 ? Commons.Color.urgent : center.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
          }
          CenterButton {
            id: remove
            anchors.right: parent.right
            y: Style.space(4)
            text: "×"
            implicitWidth: Style.space(28)
            implicitHeight: Style.space(26)
            Accessible.name: "Remove notification: " + entry.model.summary
            onClicked: { feed.forceActiveFocus(); center.action("remove:" + entry.model.key) }
          }
          MouseArea { anchors.fill: details; acceptedButtons: Qt.LeftButton; onClicked: { feed.currentIndex = entry.index; feed.forceActiveFocus() } }
          Accessible.role: Accessible.StaticText
          Accessible.name: entry.model.groupLabel + ": " + entry.model.summary + ". " + entry.model.body
        }
        Text {
          anchors.centerIn: parent
          width: parent.width - Style.space(20)
          visible: !center.rows.length
          text: !center.store.ready ? (center.store.snapshot.error || (!center.store.hostAvailable ? "Notification service unavailable.\nWaiting for Omarchy…" : "Connecting to notifications…")) : "All clear.\nNew notifications will appear here, grouped by app and website."
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
      text: center.store.snapshot.error || center.store.commandError || (!center.store.ready ? "Waiting for the notification reader and host service." : "Some entries were skipped or the list was limited to the newest 256.")
      textFormat: Text.PlainText
      wrapMode: Text.Wrap
      color: Commons.Color.urgent
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.caption
    }
    Text { width: parent.width; text: "× removes an entry from this list only. Del removes the selected entry; Shift+Del clears its group."; wrapMode: Text.Wrap; color: center.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
  }
}
