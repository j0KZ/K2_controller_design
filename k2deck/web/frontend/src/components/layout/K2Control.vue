<template>
  <div
    class="k2-control relative cursor-pointer rounded-lg transition-all duration-150"
    :class="[
      isSelected && 'control-selected',
      'hover:bg-k2-surface-hover',
    ]"
    @click="handleClick"
  >
    <component
      :is="controlComponent"
      :control="control"
      :led-state="ledState"
      :analog-value="analogValue"
      :mapping="mapping"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useUi } from '@/stores/ui'
import { useK2State } from '@/stores/k2State'
import { useAnalogState } from '@/stores/analogState'
import { useConfig } from '@/stores/config'
import K2Button from './K2Button.vue'
import K2Encoder from './K2Encoder.vue'
import K2Pot from './K2Pot.vue'
import K2Fader from './K2Fader.vue'

const props = defineProps({
  control: { type: Object, required: true },
  rowType: { type: String, required: true },
})

const ui = useUi()
const k2State = useK2State()
const analogState = useAnalogState()
const config = useConfig()

const controlComponent = computed(() => {
  switch (props.control.type) {
    case 'encoder': return K2Encoder
    case 'pot': return K2Pot
    case 'fader': return K2Fader
    default: return K2Button
  }
})

const isSelected = computed(() =>
  ui.selectedControl?.id === props.control.id
)

const ledState = computed(() =>
  props.control.hasLed ? k2State.getLedState(props.control.note || props.control.pushNote) : null
)

const analogValue = computed(() =>
  props.control.cc !== undefined ? analogState.getPosition(props.control.cc) : null
)

const mapping = computed(() =>
  config.getMappingForControl(props.control)
)

function handleClick() {
  ui.selectControl(props.control)
}
</script>
