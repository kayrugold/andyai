# Migration Map

This is the working placement map for the remaining repo while we continue turning the architecture into code.

## Active Package Model

- `subsystems/os`: subconscious/background machinery
- `subsystems/ai`: conscious presentation and narration
- `subsystems/linguistic`: word, phonetic, voice, and language organs
- `subsystems/creative`: internal creative capability domains A.N.D.Y. can learn and reshape
- `subsystems/regulation`: nervous system, reflexes, pressure, recovery, cross-system signaling
- `runtime`: composition, bootstrapping, worker/thread startup, app wiring
- `plugins/mentors`: optional external teacher/tool adapters such as Gemini or Ollama

## Already Landed

- `subsystems/os`
  - `andy_os.py`
  - `autotrain_support.py`
  - `conscious_surface.py`
  - `diagnostics_support.py`
  - `left_brain.py`
  - `memory_reasoning.py`
  - `status_reports.py`
  - `strategy_system.py`
  - `working_memory.py`
- `subsystems/ai`
  - `andy_ai.py`
  - `conscious_interface.py`
- `subsystems/creative`
  - `art_engine.py`
- `subsystems/regulation`
  - `nervous_system.py`
- `runtime`
  - `context.py`
  - `foundation.py`
  - `boot.py`
  - `background_threads.py`

## Next Clear Homes

- `runtime`
  - `cli_loop.py`
  - `task_queue.py`
  - `workers.py`
  - `language_commands.py`
  - `language_learning_commands.py`
  - `language_world_commands.py`
  - `language_training_commands.py`
  - `language_speech_commands.py`
  - `runtime_boot.py` remains as compatibility shim
  - `background_threads.py` remains as compatibility shim
- `subsystems/linguistic`
  - `linguistic_sieve.py`
  - `voice_box.py`
  - `sentence_memory.py`
  - `model_evolution_handler.py`
  - `word_model_evolution_handler.py`
  - `word_memmap_core.py`
  - `andy_memmap_core.py`
  - `andy_memmap_bridge.py`
- `subsystems/os`
  - `dream_engine.py`
  - `drive_scheduler.py`
  - `embedder.py`
  - `fitness.py`
  - `exploration_engine.py`
  - `goals.py`
  - `planner.py`
  - `recall.py`
  - `reasoner.py`
  - `reflector.py`
  - `recovery_engine.py`
  - `concept_clusters.py`
  - `concept_graph.py`
  - `theme_memory.py`
  - `taste_memory.py`
  - `scene_variation_engine.py`
  - `mutation_lanes.py`
  - `identity_notes.py`
  - `aesthetic_engine.py`
  - `evolver.py`
- `subsystems/ai`
  - `conversational_engine.py`
- `plugins/mentors`
  - `gemini.py`
  - `base.py`
  - future `ollama.py`
- `runtime` or shared infrastructure
  - `galaxy.py`
  - `archive_commands.py`

- `infra/storage`
  - `memory_store.py`
  - `state_store.py`

- `infra/tools`
  - `tool_registry.py`
  - `tools_basic.py`
- `infra/retrieval`
  - `retrieval_utils.py`

## Needs Split First
- `art_engine.py`
  - moved to `subsystems/creative`
- `art_commands.py`
  - runtime command layer over creative capabilities
- `memory_commands.py`
  - may stay command-facing, or split between runtime command handling and OS memory operations
- `regulation_commands.py`
  - likely runtime command handling over regulation services

## Compatibility Policy

- Keep top-level shims while imports are still mixed.
- Prefer updating new code to import from package paths directly.
- Remove shims only after `rg` shows the old path is no longer used.
