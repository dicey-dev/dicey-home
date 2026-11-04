import QtQuick
import QtQuick.Controls
import qs.Commons
import qs.Commons as Commons

Button {
  id: button
  property bool accented: false
  implicitHeight: Style.space(34)
  implicitWidth: Math.max(Style.space(36), label.implicitWidth + Style.space(24))
  padding: Style.space(8)
  opacity: enabled ? 1 : 0.4
  background: Rectangle {
    radius: Math.min(Style.cornerRadius, Style.space(4))
    color: button.accented ? Commons.Color.accent : Util.alpha(Color.menu.text, button.hovered || button.activeFocus ? 0.12 : 0.045)
    border.width: Style.spacing.hairline
    border.color: button.activeFocus ? Commons.Color.accent : Util.alpha(Color.menu.text, 0.18)
  }
  contentItem: Text {
    id: label
    text: button.text
    textFormat: Text.PlainText
    font.family: Style.font.menuFamily
    font.pixelSize: Style.font.caption
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    color: Color.menu.text
  }
}
