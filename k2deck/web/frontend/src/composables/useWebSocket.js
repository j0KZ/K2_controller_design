import { ref } from 'vue'
import ReconnectingWebSocket from 'reconnecting-websocket'
import { useK2State } from '@/stores/k2State'
import { useAnalogState } from '@/stores/analogState'
import { useMidi } from '@/stores/midi'
import { useIntegrations } from '@/stores/integrations'
import { useProfiles } from '@/stores/profiles'

export function useWebSocket() {
  const ws = ref(null)
  const connected = ref(false)

  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/ws/events`

    ws.value = new ReconnectingWebSocket(url, [], {
      maxReconnectionDelay: 10000,
      minReconnectionDelay: 1000,
      reconnectionDelayGrowFactor: 1.3,
    })

    ws.value.onopen = () => { connected.value = true }
    ws.value.onclose = () => { connected.value = false }
    ws.value.onmessage = (event) => handleMessage(JSON.parse(event.data))
  }

  function handleMessage(msg) {
    const k2State = useK2State()
    const analogState = useAnalogState()
    const midi = useMidi()
    const integrations = useIntegrations()
    const profiles = useProfiles()

    switch (msg.type) {
      case 'midi_event':
        midi.addEvent(msg.data)
        break
      case 'led_change':
        k2State.handleLedChange(msg.data)
        break
      case 'layer_change':
        k2State.setLayer(msg.data.layer)
        break
      case 'folder_change':
        k2State.setFolder(msg.data.folder)
        break
      case 'connection_change':
        k2State.setConnection(msg.data.connected, msg.data.port)
        break
      case 'integration_change':
        integrations.handleChange(msg.data.name, msg.data.status)
        break
      case 'profile_change':
        profiles.handleChange(msg.data.profile)
        break
      case 'analog_change':
        analogState.handleChange(msg.data.cc, msg.data.value)
        break
      case 'analog_state':
        analogState.initFromState(msg.data.controls)
        break
    }
  }

  function send(type, data) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type, data }))
    }
  }

  function disconnect() {
    ws.value?.close()
  }

  return { connect, disconnect, connected, send }
}
