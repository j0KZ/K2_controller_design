/**
 * Canonical action groups aligned with backend ACTION_TYPES (mapping_engine.py:70-129).
 * Single source of truth — imported by ActionPicker, ActionCatalog, and tests.
 */
export const ACTION_GROUPS = {
  Media: [
    'spotify_play_pause', 'spotify_next', 'spotify_previous',
    'spotify_volume', 'spotify_like', 'spotify_shuffle', 'spotify_repeat',
    'spotify_seek', 'spotify_prev_next',
    'media_key',
  ],
  System: [
    'hotkey', 'hotkey_relative', 'volume', 'mouse_scroll',
    'open_url', 'clipboard_paste', 'launch', 'focus',
  ],
  Audio: [
    'sound_play', 'sound_stop', 'audio_switch', 'audio_list',
  ],
  OBS: [
    'obs_scene', 'obs_source_toggle', 'obs_stream', 'obs_record', 'obs_mute',
  ],
  Twitch: [
    'twitch_marker', 'twitch_clip', 'twitch_chat', 'twitch_title', 'twitch_game',
  ],
  OSC: [
    'osc_send', 'osc_send_relative', 'osc_send_trigger',
  ],
  Timers: [
    'timer_start', 'timer_stop', 'timer_toggle',
  ],
  Advanced: [
    'conditional', 'multi', 'multi_toggle',
    'folder', 'folder_back', 'folder_root',
    'counter', 'tts',
  ],
  Utility: ['noop', 'system'],
}

export function formatActionName(type) {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
