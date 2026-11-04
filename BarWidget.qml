import QtQuick
import qs.Ui
import qs.Commons
import qs.Commons as Commons
import "home" as Home

BarWidget {
  id: root
  moduleName: "dicey.home"
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "\ue900"
    fontFamily: "omarchy"
    labelVisible: false
    fixedWidth: root.vertical ? root.barSize : status.implicitWidth + Style.space(15)
    tooltipText: "Home notifications · " + (Home.NotificationStore.ready ? Home.NotificationStore.unreadCount + " unread" : "connecting") + (Home.NotificationStore.snapshot.dnd === true ? " · Do not disturb" : "")
    Accessible.name: tooltipText
    horizontalMargin: 7.5
    onPressed: function(button) {
      if (!root.bar) return
      if (button === Qt.RightButton) root.bar.run("xdg-terminal-exec")
      else root.bar.run("omarchy-shell shell summon " + root.moduleName + " '{\"menu\":\"root\",\"view\":\"notifications\"}'")
    }
    Row {
      id: status
      anchors.centerIn: parent
      spacing: Style.space(4)
      Text { text: "\ue900"; color: button.foreground; font.family: "omarchy"; font.pixelSize: button.fontSize }
      Text { visible: !root.vertical && text.length > 0; text: (Home.NotificationStore.ready ? Home.NotificationStore.badge : "!") + (Home.NotificationStore.snapshot.dnd === true ? " Ⅱ" : ""); color: Home.NotificationStore.urgent ? Commons.Color.urgent : Commons.Color.accent; font.family: Style.font.family; font.pixelSize: Style.font.caption; font.bold: true }
    }
    Rectangle { visible: root.vertical && (Home.NotificationStore.unreadCount > 0 || Home.NotificationStore.snapshot.dnd === true); anchors.right: parent.right; anchors.top: parent.top; anchors.margins: Style.space(3); width: Style.space(5); height: width; radius: width / 2; color: Home.NotificationStore.urgent ? Commons.Color.urgent : Commons.Color.accent }
  }
}
