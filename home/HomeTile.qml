import QtQuick
import qs.Commons
import qs.Ui

BorderSurface {
  id: tile
  default property alias contents: body.data
  property string tileId: ""
  property string title: ""
  property string caption: ""
  property string detail: ""
  property string glyph: ""
  property string iconSource: ""
  property real iconSize: Style.space(44)
  readonly property bool iconReady: appIcon.status === Image.Ready
  property color foreground: Color.menu.text
  property color tileColor: Qt.tint(Color.menu.background, Util.alpha(Color.menu.text, 0.045))
  property bool interactive: true
  property bool editing: false
  property bool pinned: true
  property var home: null
  property int rowIndex: -1
  property string resultId: ""
  signal activated()
  signal pinRequested()
  color: hover.containsMouse && interactive ? Qt.tint(tileColor, Util.alpha(foreground, 0.055)) : tileColor
  radius: Math.min(Style.cornerRadius, Style.space(4))
  borderSpec: activeFocus ? Border.flat(Color.accent, Style.space(2)) : Border.flat(Util.alpha(foreground, 0.16), Style.spacing.hairline)
  opacity: pinned ? 1 : 0.4
  activeFocusOnTab: true
  Accessible.role: interactive ? Accessible.Button : Accessible.Grouping
  Accessible.name: title + (detail ? ", " + detail : "")
  onActiveFocusChanged: if (activeFocus && home) home.tileFocused(tile)
  Component.onCompleted: if (home) home.registerTile(tile)
  Component.onDestruction: if (home) home.unregisterTile(tile)
  function focusFirstControl(item) {
    var children = item.children || []
    for (var i = 0; i < children.length; i++) {
      var child = children[i]
      if (!child.visible || !child.enabled) continue
      if (child.activeFocusOnTab) { child.forceActiveFocus(); return true }
      if (focusFirstControl(child)) return true
    }
    return false
  }
  Keys.onPressed: function(event) {
    if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
      if (interactive) activated()
      else focusFirstControl(body)
      event.accepted = true
    }
  }
  MouseArea {
    id: hover
    anchors.fill: parent
    hoverEnabled: true
    enabled: tile.interactive
    cursorShape: Qt.PointingHandCursor
    onClicked: { tile.forceActiveFocus(); tile.activated() }
  }
  Text {
    id: heading
    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
    anchors.margins: Style.space(16)
    text: tile.caption.toUpperCase()
    textFormat: Text.PlainText
    elide: Text.ElideRight
    color: tile.foreground
    font.family: Style.font.menuFamily
    font.pixelSize: Style.font.caption
    font.letterSpacing: Style.space(0.5)
  }
  Item {
    id: body
    anchors.left: parent.left; anchors.right: parent.right
    anchors.top: heading.bottom; anchors.bottom: footer.top
    anchors.leftMargin: Style.space(16); anchors.rightMargin: Style.space(16)
    anchors.topMargin: Style.space(12); anchors.bottomMargin: Style.space(10)
    Text {
      visible: tile.glyph !== "" && !tile.iconReady
      anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
      text: tile.glyph
      color: tile.foreground
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.displayLarge * 1.2
    }
    Image {
      id: appIcon
      anchors.left: parent.left
      anchors.top: parent.top
      width: tile.iconSize; height: width
      source: tile.iconSource
      sourceSize.width: width * Screen.devicePixelRatio
      sourceSize.height: height * Screen.devicePixelRatio
      fillMode: Image.PreserveAspectFit
      asynchronous: true
      visible: tile.iconReady
    }
  }
  Text {
    id: footer
    anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
    anchors.margins: Style.space(16)
    text: tile.title + (tile.detail ? "  ·  " + tile.detail : "")
    textFormat: Text.PlainText
    elide: Text.ElideRight
    color: tile.foreground
    font.family: Style.font.menuFamily
    font.pixelSize: Style.font.caption
  }
  Loader {
    active: tile.editing && tile.tileId !== ""
    anchors.right: parent.right; anchors.top: parent.top; anchors.margins: Style.space(4)
    z: 5
    sourceComponent: HomeButton {
      text: tile.pinned ? "−" : "+"
      Accessible.name: (tile.pinned ? "Hide " : "Show ") + tile.title
      onClicked: tile.pinRequested()
    }
  }
}
