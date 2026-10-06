"""
Generates 5 realistic-looking AUTOSAR HLD sample PDFs for demoing the
assistant end-to-end (upload -> ask -> extract -> compare -> export).
Includes a v1/v2 revision pair (Body Control Module) so the Compare tab
has something meaningful to diff.

Run with:  venv\\Scripts\\python scripts\\generate_samples.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import fitz  # PyMuPDF

OUT_DIR = PROJECT_ROOT / "sample_documents"
OUT_DIR.mkdir(exist_ok=True)

HEADING_SIZE = 15
SUBHEADING_SIZE = 12
BODY_SIZE = 10
MARGIN_X = 56
PAGE_W, PAGE_H = fitz.paper_size("a4")


class PdfBuilder:
    def __init__(self):
        self.doc = fitz.open()
        self.page = None
        self.y = 0

    def new_page(self):
        self.page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        self.y = 60

    def _ensure_space(self, needed=20):
        if self.y + needed > PAGE_H - 50:
            self.new_page()

    def title(self, text):
        self.new_page()
        self.page.insert_text((MARGIN_X, self.y), text, fontsize=20, fontname="helv", color=(0.05, 0.1, 0.3))
        self.y += 34
        self.page.draw_line((MARGIN_X, self.y), (PAGE_W - MARGIN_X, self.y), color=(0.6, 0.6, 0.6), width=0.5)
        self.y += 24

    def heading(self, text):
        self._ensure_space(40)
        self.y += 14
        self.page.insert_text(
            (MARGIN_X, self.y), text, fontsize=HEADING_SIZE, fontname="hebo", color=(0.05, 0.1, 0.3)
        )
        self.y += 22

    def subheading(self, text):
        self._ensure_space(30)
        self.page.insert_text(
            (MARGIN_X, self.y), text, fontsize=SUBHEADING_SIZE, fontname="hebo", color=(0.1, 0.15, 0.35)
        )
        self.y += 18

    def para(self, text, indent=0):
        for line in text.split("\n"):
            self._ensure_space(16)
            self.page.insert_text(
                (MARGIN_X + indent, self.y), line, fontsize=BODY_SIZE, fontname="helv", color=(0.1, 0.1, 0.1)
            )
            self.y += 15

    def bullet(self, text):
        self.para(f"  -  {text}")

    def spacer(self, h=10):
        self.y += h

    def save(self, filename):
        path = OUT_DIR / filename
        self.doc.save(str(path))
        self.doc.close()
        print(f"Created {path}")


def build_body_control_v1():
    b = PdfBuilder()
    b.title("Body Control Module - High-Level Design (Rev A)")

    b.heading("1. Component Overview")
    b.para(
        "This document describes the High-Level Design of the Body Control Module "
        "software cluster, covering lighting, door, and window control functions."
    )
    b.spacer()
    b.subheading("Software Components")
    b.para("Component: BodyControlModuleComponent")
    b.para("Component: LightingManagerComponent")
    b.para("Component: DoorControlComponent")
    b.para("The BodyControlModuleComponent acts as the central coordinator for all body domain functions.")

    b.heading("2. Interfaces and Ports")
    b.para("Interface: LightingControlInterface")
    b.para("Interface: DoorStatusInterface")
    b.para("PPort: LightingManager_PPort")
    b.para("RPort: DoorControl_RPort")
    b.para(
        "LightingManagerComponent provides LightingControlInterface via LightingManager_PPort. "
        "DoorControlComponent requires DoorStatusInterface via DoorControl_RPort."
    )

    b.heading("3. Signals")
    b.para("Signal: HeadlampState_Signal")
    b.para("Signal: DoorAjar_Signal")
    b.para("Signal: IndicatorRequest_Signal")

    b.heading("4. Dependencies")
    b.para(
        "BodyControlModuleComponent depends on LightingManagerComponent for lighting state "
        "and on DoorControlComponent for door status aggregation."
    )

    b.heading("5. Functional Flow")
    b.para(
        "On receiving an IndicatorRequest_Signal, LightingManagerComponent evaluates the "
        "current HeadlampState_Signal and issues the appropriate lamp actuation command "
        "within 100 ms, as required by the body domain timing budget."
    )

    b.save("BodyControlModule_HLD_RevA.pdf")


def build_body_control_v2():
    b = PdfBuilder()
    b.title("Body Control Module - High-Level Design (Rev B)")

    b.heading("1. Component Overview")
    b.para(
        "This document describes the High-Level Design of the Body Control Module "
        "software cluster, covering lighting, door, window, and mirror control functions. "
        "Revision B adds mirror control support."
    )
    b.spacer()
    b.subheading("Software Components")
    b.para("Component: BodyControlModuleComponent")
    b.para("Component: LightingManagerComponent")
    b.para("Component: DoorControlComponent")
    b.para("Component: MirrorControlComponent")
    b.para("The BodyControlModuleComponent acts as the central coordinator for all body domain functions.")

    b.heading("2. Interfaces and Ports")
    b.para("Interface: LightingControlInterface")
    b.para("Interface: DoorStatusInterface")
    b.para("Interface: MirrorPositionInterface")
    b.para("PPort: LightingManager_PPort")
    b.para("RPort: DoorControl_RPort")
    b.para("PPort: MirrorControl_PPort")
    b.para(
        "LightingManagerComponent provides LightingControlInterface via LightingManager_PPort. "
        "DoorControlComponent requires DoorStatusInterface via DoorControl_RPort. "
        "MirrorControlComponent provides MirrorPositionInterface via MirrorControl_PPort."
    )

    b.heading("3. Signals")
    b.para("Signal: HeadlampState_Signal")
    b.para("Signal: DoorAjar_Signal")
    b.para("Signal: IndicatorRequest_Signal")
    b.para("Signal: MirrorPosition_Signal")

    b.heading("4. Dependencies")
    b.para(
        "BodyControlModuleComponent depends on LightingManagerComponent for lighting state, "
        "on DoorControlComponent for door status aggregation, and on MirrorControlComponent "
        "for mirror position feedback introduced in this revision."
    )

    b.heading("5. Functional Flow")
    b.para(
        "On receiving an IndicatorRequest_Signal, LightingManagerComponent evaluates the "
        "current HeadlampState_Signal and issues the appropriate lamp actuation command "
        "within 80 ms, tightened from the previous 100 ms budget in Rev A."
    )

    b.heading("6. Revision Notes")
    b.para("Added MirrorControlComponent and MirrorPositionInterface.")
    b.para("Tightened lamp actuation timing budget from 100 ms to 80 ms.")

    b.save("BodyControlModule_HLD_RevB.pdf")


def build_powertrain():
    b = PdfBuilder()
    b.title("Powertrain Control - High-Level Design")

    b.heading("1. Component Overview")
    b.para(
        "This document defines the architecture of the Powertrain Control software, "
        "responsible for engine and transmission coordination."
    )
    b.subheading("Software Components")
    b.para("Component: EngineControllerComponent")
    b.para("Component: TransmissionManagerComponent")
    b.para("Component: FuelInjectionComponent")

    b.heading("2. Interfaces and Ports")
    b.para("Interface: EngineTorqueInterface")
    b.para("Interface: GearShiftInterface")
    b.para("PPort: EngineController_PPort")
    b.para("RPort: TransmissionManager_RPort")
    b.para(
        "EngineControllerComponent provides EngineTorqueInterface via EngineController_PPort, "
        "consumed by TransmissionManagerComponent via TransmissionManager_RPort."
    )

    b.heading("3. Signals")
    b.para("Signal: EngineSpeed_Signal")
    b.para("Signal: RequestedTorque_Signal")
    b.para("Signal: GearPosition_Signal")

    b.heading("4. Dependencies")
    b.para(
        "TransmissionManagerComponent depends on EngineControllerComponent for torque "
        "availability before initiating a gear shift. FuelInjectionComponent depends on "
        "EngineControllerComponent for requested torque."
    )

    b.heading("5. Functional Flow")
    b.para(
        "EngineControllerComponent computes RequestedTorque_Signal from accelerator pedal "
        "input and publishes EngineSpeed_Signal at a 10 ms cycle time. TransmissionManagerComponent "
        "consumes both signals to determine GearPosition_Signal transitions."
    )

    b.save("PowertrainControl_HLD.pdf")


def build_infotainment():
    b = PdfBuilder()
    b.title("Infotainment Gateway - High-Level Design")

    b.heading("1. Component Overview")
    b.para(
        "This document describes the Infotainment Gateway responsible for bridging "
        "in-vehicle network signals to the infotainment domain."
    )
    b.subheading("Software Components")
    b.para("Component: ComGatewayComponent")
    b.para("Component: MediaPlayerComponent")
    b.para("Component: DiagnosticManagerComponent")

    b.heading("2. Interfaces and Ports")
    b.para("Interface: ComGatewayInterface")
    b.para("Interface: MediaControlInterface")
    b.para("PPort: ComGateway_PPort")
    b.para("RPort: MediaPlayer_RPort")
    b.para(
        "ComGatewayComponent provides ComGatewayInterface via ComGateway_PPort. "
        "MediaPlayerComponent requires MediaControlInterface via MediaPlayer_RPort."
    )

    b.heading("3. Signals")
    b.para("Signal: VehicleSpeed_Signal")
    b.para("Signal: MediaPlayState_Signal")
    b.para("Signal: DiagnosticTroubleCode_Signal")

    b.heading("4. Dependencies")
    b.para(
        "MediaPlayerComponent depends on ComGatewayComponent for vehicle speed data used to "
        "restrict video playback while driving. DiagnosticManagerComponent depends on "
        "ComGatewayComponent for network-wide diagnostic trouble codes."
    )

    b.heading("5. Functional Flow")
    b.para(
        "ComGatewayComponent relays VehicleSpeed_Signal from the vehicle network to the "
        "infotainment domain. MediaPlayerComponent evaluates this signal before allowing "
        "MediaPlayState_Signal transitions to the Playing state."
    )

    b.save("InfotainmentGateway_HLD.pdf")


def build_adas():
    b = PdfBuilder()
    b.title("ADAS Sensor Fusion - High-Level Design")

    b.heading("1. Component Overview")
    b.para(
        "This document describes the Sensor Fusion software responsible for combining "
        "radar and camera data for advanced driver assistance functions."
    )
    b.subheading("Software Components")
    b.para("Component: SensorFusionComponent")
    b.para("Component: RadarProcessingComponent")
    b.para("Component: CameraProcessingComponent")

    b.heading("2. Interfaces and Ports")
    b.para("Interface: RadarDataInterface")
    b.para("Interface: CameraDataInterface")
    b.para("Interface: FusedObjectListInterface")
    b.para("PPort: SensorFusion_PPort")
    b.para("RPort: RadarProcessing_RPort")
    b.para("RPort: CameraProcessing_RPort")
    b.para(
        "SensorFusionComponent requires RadarDataInterface via RadarProcessing_RPort and "
        "CameraDataInterface via CameraProcessing_RPort, and provides FusedObjectListInterface "
        "via SensorFusion_PPort."
    )

    b.heading("3. Signals")
    b.para("Signal: RadarObjectList_Signal")
    b.para("Signal: CameraObjectList_Signal")
    b.para("Signal: FusedObjectList_Signal")

    b.heading("4. Dependencies")
    b.para(
        "SensorFusionComponent depends on RadarProcessingComponent and CameraProcessingComponent "
        "for raw object lists, and produces a time-aligned FusedObjectList_Signal at a 20 ms cycle."
    )

    b.heading("5. Functional Flow")
    b.para(
        "RadarProcessingComponent and CameraProcessingComponent independently publish object "
        "lists. SensorFusionComponent time-aligns and merges these into FusedObjectList_Signal, "
        "which is consumed by downstream ADAS decision components."
    )

    b.save("ADAS_SensorFusion_HLD.pdf")


if __name__ == "__main__":
    build_body_control_v1()
    build_body_control_v2()
    build_powertrain()
    build_infotainment()
    build_adas()
    print("\nAll 5 sample PDFs generated in:", OUT_DIR)
