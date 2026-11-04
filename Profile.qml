import QtQuick
import QtQuick.Effects
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons

Item {
  id: profile

  property string username: Quickshell.env("USER") || "You"
  property string picturePath: ""
  property double pictureVersion: 0
  readonly property bool pictureReady: portrait.status === Image.Ready
  readonly property string initials: {
    var names = username.trim().split(/[\s._-]+/).filter(function(name) { return !!name })
    return names.length ? (names[0].charAt(0) + (names.length > 1 ? names[names.length - 1].charAt(0) : "")).toUpperCase() : "?"
  }

  implicitHeight: Style.space(32)
  implicitWidth: Math.min(nameText.implicitWidth, Style.space(120)) + Style.space(12) + implicitHeight

  function refresh() {
    if (!pictureLookup.running) pictureLookup.running = true
  }

  // Resolve existing files before asking Image to load them, so systems with
  // no avatar get a quiet initials fallback. Paths are passed as data only.
  Process {
    id: pictureLookup
    command: ["bash", "-c", 'for image in "$HOME/.config/omarchy/launcher-avatar" "$HOME/.face" "$HOME/.face.icon" "/var/lib/AccountsService/icons/$USER"; do if [[ -f $image && -r $image ]]; then printf "%s" "$image"; break; fi; done']
    stdout: StdioCollector { id: pictureOutput; waitForEnd: true }
    onExited: function(code) {
      profile.picturePath = code === 0 ? String(pictureOutput.text || "") : ""
      profile.pictureVersion = Date.now()
    }
  }

  Column {
    anchors.left: parent.left
    anchors.right: avatar.left
    anchors.rightMargin: Style.space(12)
    anchors.verticalCenter: parent.verticalCenter
    spacing: Style.space(2)

    Text {
      id: nameText
      width: parent.width
      text: profile.username
      textFormat: Text.PlainText
      horizontalAlignment: Text.AlignRight
      elide: Text.ElideRight
      color: Color.menu.text
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.bodySmall
      font.weight: Font.Medium
    }
    Text {
      width: parent.width
      text: "LOCAL SESSION"
      horizontalAlignment: Text.AlignRight
      color: Color.menu.text
      opacity: 0.5
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.caption
    }
  }

  Rectangle {
    id: avatar
    width: profile.height
    height: width
    anchors.right: parent.right
    anchors.verticalCenter: parent.verticalCenter
    radius: width / 2
    color: Util.alpha(Commons.Color.accent, 0.12)
    border.width: Style.spacing.hairline
    border.color: Util.alpha(Commons.Color.accent, 0.45)

    Text {
      anchors.centerIn: parent
      visible: !profile.pictureReady
      text: profile.initials
      color: Commons.Color.accent
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.body
      font.weight: Font.DemiBold
    }

    Item {
      id: portraitMask
      anchors.fill: portraitSurface
      visible: false
      layer.enabled: true
      Rectangle { anchors.fill: parent; radius: width / 2; color: "white"; antialiasing: true }
    }
    Item {
      id: portraitSurface
      anchors.fill: parent
      anchors.margins: Math.max(Style.spacing.hairline, Style.space(1))
      visible: profile.pictureReady
      layer.enabled: true
      layer.smooth: true
      layer.effect: MultiEffect {
        maskEnabled: true
        maskSource: portraitMask
        maskThresholdMin: 0.3
        maskSpreadAtMin: 0.3
      }

      Image {
        id: portrait
        anchors.fill: parent
        source: profile.picturePath ? Util.fileUrl(profile.picturePath) + "?v=" + profile.pictureVersion : ""
        sourceSize.width: width * Screen.devicePixelRatio
        sourceSize.height: height * Screen.devicePixelRatio
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: false
        smooth: true
      }
    }
  }
}
