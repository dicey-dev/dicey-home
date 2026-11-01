import QtQuick
import QtQuick.Controls
import qs.Commons

Slider {
  id: slider
  implicitHeight: Style.space(28)
  padding: 0
  opacity: enabled ? 1 : 0.35
  background: Rectangle {
    x: slider.leftPadding
    y: slider.topPadding + slider.availableHeight / 2 - height / 2
    width: slider.availableWidth
    height: Style.space(3)
    radius: height / 2
    color: Util.alpha(Color.menu.text, 0.2)
    Rectangle { width: slider.visualPosition * parent.width; height: parent.height; radius: parent.radius; color: Color.accent }
  }
  handle: Rectangle {
    x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
    y: slider.topPadding + slider.availableHeight / 2 - height / 2
    width: Style.space(12); height: width; radius: width / 2
    color: Color.accent
    border.width: slider.activeFocus ? Style.spacing.hairline : 0
    border.color: Color.menu.text
  }
}
