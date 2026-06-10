export type SceneChoreography = {
  scene_id: number;
  scene_title: string;
  narration: string;
  on_screen_text: string;
  svg_markup: string;
  metaphor_hint: string;
  audio_path: string;
  svg_path: string;
  svg_content: string;
  audio_duration_ms: number;
  draw_start_ms: number;
  draw_duration_ms: number;
  hold_ms: number;
  // Infinite-canvas spatial fields
  canvas_x: number;
  canvas_y: number;
  canvas_width: number;
  canvas_height: number;
  layout_direction: string;
  kinetic_words: string[];
  // Secondary SVG for dual-illustration layout
  svg_content_secondary?: string | null;
  svg_path_secondary?: string | null;
};

export type RenderProps = {
  fps: number;
  width: number;
  height: number;
  scenes: SceneChoreography[];
};


