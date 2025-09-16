export type ServerInfo = {
  type: 'info'
  message: string
}

export type ServerError = {
  type: 'error'
  reason: string
}

export type NarrativeUpdate = {
  type: 'narrative_update'
  session_id: string
  turn_id: number
  text: string
  image?: string | null
  voice_audio?: string | null
  music?: string | null
}

export type OverrideUpdate = {
  type: 'override_update'
  session_id: string
  turn_id: number
  text?: string | null
  image?: string | null
  voice_audio?: string | null
  music?: string | null
}

export type StoryUpdate = {
  type: 'story_update'
  session_id: string
  turn_id: number
  text: string
  whispers: string[]
  tags: any
  shot?: string
  metrics: any
  metrics_delta: any
  inventory: any
  location: string
  relations: any
  casefile: any
  reframed: boolean
  reframed_from?: string
  reframed_to?: string
  image?: string
  voice_audio?: string
  sfx?: string[]
}

export type ImageUpdate = {
  type: 'image_update'
  session_id: string
  turn_id: number
  image: string
}

export type ServerMsg = ServerInfo | ServerError | NarrativeUpdate | OverrideUpdate | StoryUpdate | ImageUpdate

export type ClientAction = {
  type: 'action'
  player: string
  session_id: string
  turn_id: number
  text_raw: string
}
