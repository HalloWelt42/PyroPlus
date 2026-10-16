/* Typen der Schnittstelle. Sie spiegeln die Pydantic-Modelle des Backends (camelCase). */

export type OledMode = 'auto' | 'manual' | 'off';
export type Align = 'left' | 'center' | 'right';
export type Rotation = 0 | 90 | 180 | 270;
export type ValueType = 'number' | 'percent' | 'string' | 'time' | 'animated' | 'shape' | 'bitmap';
export type Tab = 'cpu' | 'ram' | 'disk' | 'net' | 'fan' | 'zeit' | 'wetter' | 'text' | 'layout';
export type DisplayMode =
  | 'text' | 'text_invertiert' | 'text_rahmen'
  | 'balken' | 'balken_label' | 'balken_label_in'
  | 'gauge' | 'sparkline' | 'laufschrift'
  | 'fan_icon' | 'fan_icon_rpm'
  | 'symbol' | 'symbol_wert' | 'ring' | 'balken_v' | 'stufen' | 'sieben_segment'
  | 'linie_h' | 'linie_v' | 'rahmen' | 'block' | 'section'
  | 'bitmap';
export type ScreenKind = 'widgets' | 'weather_compact' | 'weather_hourly' | 'weather_daily';

export interface WidgetOpts {
  scaleX: number;
  scaleY: number | null;
  prefix: string;
  suffix: string;
  decimals: number | null;
  thousands: boolean;
  invert: boolean;
  border: boolean;
  align: Align;
  boxW: number;
  width: number | null;
  height: number | null;
  radius: number | null;
  size: number | null;
  text: string | null;
  rotate: Rotation;
  locationId: string | null;
  bitmap: string | null;
  icon: string | null;
  filled: boolean;
  steps: number | null;
}

export interface Widget {
  id: string;
  source: string;
  display: DisplayMode;
  x: number;
  y: number;
  name: string;
  opts: WidgetOpts;
}

export interface Screen {
  id: string;
  name: string;
  kind: ScreenKind;
  widgets: Widget[];
  locationId: string | null;
  enabled: boolean;
  duration: number | null;
}

export interface OledSettings {
  schemaVersion: number;
  mode: OledMode;
  brightness: number;
  rotationInterval: number;
  currentScreenId: string | null;
  screens: Screen[];
}

export interface OledSettingsPatch {
  mode?: OledMode;
  brightness?: number;
  rotationInterval?: number;
  currentScreenId?: string;
}

export interface OledLive {
  mode: OledMode;
  brightness: number;
  rotationInterval: number;
  currentScreenId: string | null;
  screensVersion: number;
  preview: string | null;
}

export interface OledState extends OledLive {
  available: boolean;
  hardware: boolean;
  width: number;
  height: number;
  screens: Screen[];
  weatherOk: boolean;
  version: string;
}

export interface TabInfo { id: Tab; label: string; }

export interface SourceInfo {
  id: string;
  tab: Tab;
  label: string;
  unit: string;
  valueType: ValueType;
  description: string;
  group: string;
  usesLocation: boolean;
  example: string;
}

export interface ModeVariant { id: string; label: string; opts: WidgetOpts; }

export interface DisplayModeInfo {
  id: DisplayMode;
  label: string;
  description: string;
  forTypes: ValueType[];
  fields: string[];
  defaults: WidgetOpts;
  variants: ModeVariant[];
}

export interface SymbolInfo { id: string; label: string; category: string; }

export interface Catalog {
  width: number;
  height: number;
  tabs: TabInfo[];
  sources: SourceInfo[];
  modes: DisplayModeInfo[];
  symbols: SymbolInfo[];
  symbolCategories: string[];
  symbolSizes: number[];
}

export interface WidgetBox { id: string; x: number; y: number; w: number; h: number; }
/* Vorschau eines einzelnen Widgets: Bild genau in Widgetgröße; width 0 = nichts gezeichnet */
export interface WidgetRenderResponse { imageBase64: string; width: number; height: number; box: WidgetBox; }

export interface RenderRequest { screen: Screen; simulate?: Record<string, number>; }
export interface RenderResponse { imageBase64: string; boxes: WidgetBox[]; width: number; height: number; }

export interface WidgetPreset {
  id: string;
  name: string;
  source: string;
  display: DisplayMode;
  opts: WidgetOpts;
  created: string;
}

export interface Profile {
  id: string;
  name: string;
  created: string;
  screens: Screen[];
  rotationInterval: number;
}

export interface WeatherLocation { id: string; name: string; lat: number; lon: number; country: string; }
export interface WeatherLocationCreate { name: string; lat: number; lon: number; country?: string; }
export interface WeatherSettings { locations: WeatherLocation[]; defaultLocationId: string | null; }
export interface WeatherLocationState {
  location: WeatherLocation;
  isDefault: boolean;
  fetchedAt: string | null;
  ok: boolean;
  summary: string;
}
export interface GeocodeHit { name: string; country: string; admin: string; lat: number; lon: number; }

export interface ScreenTemplate { id: string; name: string; description: string; category: string; screen: Screen; }
export interface WidgetTemplate { id: string; name: string; description: string; category: string; widget: Widget; }
export interface TemplateCatalog { screens: ScreenTemplate[]; widgets: WidgetTemplate[]; categories: string[]; }

export interface OledBundle {
  appVersion: string;
  exported: string;
  settings: OledSettings;
  presets: WidgetPreset[];
  profiles: Profile[];
  weather: WeatherSettings;
}
export interface ImportResult { screens: number; presets: number; profiles: number; locations: number; }

/* Lüfter */
export interface CurvePoint { temp: number; speed: number; }
export type FanMode = 'auto' | 'manual' | 'off';
export interface FanState {
  available: boolean;
  mode: FanMode;
  profile: string;
  curve: CurvePoint[];
  current_duty: number;
  current_temp: number;
  current_rpm: number;
  manual_speed: number;
  hysteresis: number;
  profiles: string[];
  case_on: boolean;
  case_profile: string;
  threshold_on: number;
  threshold_off: number;
  safety_temp: number;
}
export interface FanFineSettings { hysteresis?: number; threshold_on?: number; threshold_off?: number; case_profile?: string; }

/* LEDs */
export interface Rgb { r: number; g: number; b: number; }
export interface EffectMeta { name: string; category: string; icon: string; }
export interface LedState {
  available: boolean;
  effect: string;
  color: Rgb;
  color2: Rgb;
  brightness: number;
  speed: number;
  individual_mode: boolean;
  individual_colors: Rgb[];
  led_states: Rgb[];
  effects_catalog?: Record<string, EffectMeta>;
  effects_by_category?: Record<string, string[]>;
}
export type EffectCatalog = Record<string, Array<EffectMeta & { id: string }>>;

/* Systemwerte */
export interface DiskStats { label: string; mount: string; total_gb: number; used_gb: number; available_gb: number; percent: number; model?: string; fstype?: string; }
export interface Stats {
  cpu: { temp: number; temp_min: number; temp_max: number; percent: number; cores: number };
  ram: { total_gb: number; used_gb: number; available_gb: number; percent: number };
  disks: DiskStats[];
  network: { ip: string; interface: string; hostname?: string; rx_bytes_sec: number; tx_bytes_sec: number };
  fan: { pwm_level: number; rpm: number; level_name: string };
  uptime: { seconds: number; formatted: string };
  history: Record<string, number[]>;
}

export interface HwProxyHealth { status: string; version?: string; fan?: boolean; oled?: boolean; leds?: boolean; }

export interface SystemState {
  version: string;
  voll: string;
  hw_proxy: HwProxyHealth;
  fan: FanState;
  oled: OledState;
  leds: LedState;
  stats: Stats;
  custom_data: Record<string, unknown>;
}

export interface WsMessage {
  type: 'stats';
  data: { stats: Stats; fan: FanState; leds: LedState; oled: OledLive; custom_data: Record<string, unknown> };
}

export interface Ok { ok: boolean; }
