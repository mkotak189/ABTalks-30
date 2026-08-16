# Streaming Integration — Day 18

## Architecture

### Backend (FastAPI)
- `/chat` endpoint returns `StreamingResponse` with `media_type="text/event-stream"`
- Yields SSE-formatted lines: `data: {...}\n\n`
- Each SSE message contains:
  - `type: "metadata"` — initial metadata (classification, plan info)
  - `type: "token"` — single token from LLM
  - `type: "done"` — completion signal with timing
  - `type: "error"` — error message if stream fails

### Frontend (Streamlit)
- Sends `POST /chat` with `stream=True`
- Iterates over `response.iter_lines()` to consume SSE stream
- Updates UI in real-time with each token via `st.empty()` placeholder
- Shows "Streaming response..." spinner before first token
- Displays timing after stream completes

## User Experience

1. User sends message
2. Spinner appears immediately ("Streaming response...")
3. First token arrives within 1-5 seconds (model loading complete)
4. Tokens stream in real-time, text appears to "type out"
5. When done, timing appears (e.g., "⏱️ 45.2ms")
6. Message stored in session history

## Error Handling

| Scenario | Behavior | User Sees |
|---|---|---|
| Network error | Stream closes, exception caught | "Cannot connect to backend" error |
| Timeout (>120s) | Raises `requests.exceptions.Timeout` | "Request timed out. Model may be loading." |
| Mid-stream error | Backend yields `type: "error"` | Error message displayed, stream stops |
| Ollama offline | Connection refused immediately | "Cannot connect to backend" error |

## Performance Notes

- **First request:** 30-90 seconds (model loads into VRAM)
- **Subsequent requests:** 5-15 seconds (model stays in memory)
- **Token rate:** ~2-5 tokens/second on CPU, 20+ tokens/second on GPU
- **Max timeout:** 120 seconds (configurable)

## Testing Checklist

- [ ] Send a message and watch it stream in real-time
- [ ] Spinner appears before first token
- [ ] Timing displays after completion
- [ ] Message appears in chat history after stream ends
- [ ] Try "New Conversation" and verify old messages cleared
- [ ] Send 3+ sequential messages in one session
- [ ] Verify session_id persists across messages (check browser devtools)

## Known Limitations

- No mid-stream cancellation (user must wait or close browser tab)
- Very long responses (1000+ tokens) may take 1-2 minutes
- Streamlit reruns entire app on each state change (inherent limitation)