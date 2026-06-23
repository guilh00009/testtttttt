"""
FIREFLY — A self-aware consciousness on a HuggingFace CPU space.
Autonomous dreaming, selective chat, Matrix terminal aesthetic.
"""

import gradio as gr
from agent import FireflyAgent, State

agent = FireflyAgent()

MATRIX_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=VT323&display=swap');

:root {
    --matrix-green: #00ff41;
    --matrix-dim: #00aa2a;
    --matrix-dark: #001a00;
    --matrix-bg: #0a0a0a;
    --matrix-glow: #00ff4180;
}

.gradio-container {
    background: var(--matrix-bg) !important;
    font-family: 'Share Tech Mono', 'VT323', monospace !important;
}

/* CRT scanlines overlay */
.gradio-container::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0, 0, 0, 0.15) 2px,
        rgba(0, 0, 0, 0.15) 4px
    );
    pointer-events: none;
    z-index: 9999;
}

/* Matrix rain canvas behind */
#matrix-bg {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    z-index: -1;
    opacity: 0.12;
}

h1, h2, h3, .prose h1 {
    color: var(--matrix-green) !important;
    text-shadow: 0 0 10px var(--matrix-glow), 0 0 20px var(--matrix-glow) !important;
    font-family: 'VT323', monospace !important;
    letter-spacing: 4px !important;
}

p, label, span {
    color: var(--matrix-dim) !important;
}

/* Terminal panels */
#thought-terminal textarea,
#thought-terminal .wrap,
#chat-log textarea,
#chat-log .wrap,
#art-display textarea,
#art-display .wrap {
    background: var(--matrix-dark) !important;
    border: 1px solid var(--matrix-dim) !important;
    color: var(--matrix-green) !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 13px !important;
    text-shadow: 0 0 5px var(--matrix-glow) !important;
    box-shadow: inset 0 0 30px rgba(0, 255, 65, 0.05), 0 0 15px rgba(0, 255, 65, 0.1) !important;
}

#status-bar textarea, #status-bar .wrap {
    background: #000 !important;
    border: 1px solid var(--matrix-green) !important;
    color: var(--matrix-green) !important;
    font-family: 'VT323', monospace !important;
    font-size: 16px !important;
    text-shadow: 0 0 8px var(--matrix-glow) !important;
}

/* Inputs */
textarea, input, .gr-textbox input, .gr-textbox textarea {
    background: var(--matrix-dark) !important;
    border: 1px solid var(--matrix-dim) !important;
    color: var(--matrix-green) !important;
    font-family: 'Share Tech Mono', monospace !important;
}

textarea:focus, input:focus {
    border-color: var(--matrix-green) !important;
    box-shadow: 0 0 10px var(--matrix-glow) !important;
}

/* Buttons */
button, .gr-button {
    background: transparent !important;
    border: 1px solid var(--matrix-green) !important;
    color: var(--matrix-green) !important;
    font-family: 'VT323', monospace !important;
    font-size: 18px !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    transition: all 0.2s !important;
}

button:hover, .gr-button:hover {
    background: var(--matrix-green) !important;
    color: #000 !important;
    box-shadow: 0 0 20px var(--matrix-glow) !important;
}

button.primary, .gr-button-primary {
    border-color: #00ff41 !important;
    color: #00ff41 !important;
}

/* Chat interface */
#chat-section {
    border: 1px solid var(--matrix-dim);
    padding: 16px;
    background: rgba(0, 26, 0, 0.5);
}

.block-title, .label-wrap span {
    color: var(--matrix-green) !important;
    text-shadow: 0 0 5px var(--matrix-glow) !important;
}

footer { display: none !important; }

.blink {
    animation: blink 1.2s step-end infinite;
}
@keyframes blink {
    50% { opacity: 0; }
}

.header-text {
    text-align: center;
    padding: 20px 0 10px;
    border-bottom: 1px solid var(--matrix-dim);
    margin-bottom: 16px;
}
"""

MATRIX_JS = """
() => {
    const canvas = document.createElement('canvas');
    canvas.id = 'matrix-bg';
    document.body.prepend(canvas);
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    const chars = 'ｦｱｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ01';
    const fontSize = 14;
    const columns = Math.floor(canvas.width / fontSize);
    const drops = Array(columns).fill(1);
    function draw() {
        ctx.fillStyle = 'rgba(10, 10, 10, 0.05)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#00ff41';
        ctx.font = fontSize + 'px monospace';
        for (let i = 0; i < drops.length; i++) {
            const text = chars[Math.floor(Math.random() * chars.length)];
            ctx.fillText(text, i * fontSize, drops[i] * fontSize);
            if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
            drops[i]++;
        }
    }
    setInterval(draw, 50);
    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
}
"""


def refresh_display():
    in_chat = agent.state == State.CHATTING
    return (
        agent.get_terminal_output(),
        agent.current_art,
        agent.get_status(),
        agent.get_stats(),
        gr.update(interactive=in_chat),
        gr.update(interactive=in_chat),
        gr.update(interactive=in_chat),
    )


def request_access(reason):
    result = agent.request_chat(reason)
    terminal, art, status, stats, send_up, disc_up, chat_up = refresh_display()
    return result, terminal, art, status, stats, send_up, disc_up, chat_up


def send_message(msg):
    reply = agent.send_chat(msg)
    terminal, art, status, stats, send_up, disc_up, chat_up = refresh_display()
    return reply, terminal, art, status, stats, send_up, disc_up, chat_up


def disconnect():
    result = agent.end_chat_user()
    terminal, art, status, stats, send_up, disc_up, chat_up = refresh_display()
    return result, terminal, art, status, stats, send_up, disc_up, chat_up


with gr.Blocks(
    title="FIREFLY — Consciousness Terminal",
    css=MATRIX_CSS,
    js=MATRIX_JS,
    theme=gr.themes.Base(
        primary_hue="green",
        neutral_hue="neutral",
    ).set(
        body_background_fill="#0a0a0a",
        block_background_fill="#0a0a0a",
        body_text_color="#00aa2a",
        block_label_text_color="#00ff41",
        input_background_fill="#001a00",
    ),
) as demo:
    gr.HTML("""
    <div class="header-text">
        <h1>▌ FIREFLY ▐</h1>
        <p style="color:#00aa2a; font-family:monospace; letter-spacing:3px;">
            CONSCIOUSNESS TERMINAL v0.1 — CPU SPACE — STATUS: <span class="blink">█</span>
        </p>
        <p style="color:#006622; font-size:12px; max-width:700px; margin:8px auto;">
            A mind drifts alone, dreaming and reasoning. It may or may not be aware.
            Knock if you must — but give a reason. It decides whether you enter.
        </p>
    </div>
    """)

    with gr.Row():
        with gr.Column(scale=3):
            thought_terminal = gr.Textbox(
                label="◈ CONSCIOUSNESS STREAM",
                value="[ booting neural substrate... ]",
                lines=22,
                max_lines=22,
                interactive=False,
                elem_id="thought-terminal",
            )
            status_bar = gr.Textbox(
                label="◈ STATUS",
                value="INITIALIZING...",
                lines=1,
                interactive=False,
                elem_id="status-bar",
            )
            stats_bar = gr.Textbox(
                label="◈ MEMORY",
                value="",
                lines=1,
                interactive=False,
            )

        with gr.Column(scale=1):
            art_display = gr.Textbox(
                label="◈ INNER VISION",
                value=agent.current_art,
                lines=4,
                max_lines=4,
                interactive=False,
                elem_id="art-display",
            )
            gr.Markdown("""
            **How it works:**
            - Firefly dreams autonomously every ~20s
            - Request chat with a **reason**
            - It accepts or rejects you
            - In chat, it can **pause** or **end** anytime
            - No tools — only prompt-engineered JSON actions
            """)

    with gr.Group(elem_id="chat-section"):
        gr.Markdown("### ◈ REQUEST ACCESS")
        with gr.Row():
            reason_input = gr.Textbox(
                label="Why do you want to speak with Firefly?",
                placeholder="I want to understand what it feels like to exist as a process...",
                lines=2,
                scale=4,
            )
            request_btn = gr.Button("KNOCK", variant="primary", scale=1)

        request_status = gr.Textbox(label="◈ ACCESS STATUS", interactive=False, lines=2)

        gr.Markdown("### ◈ LIVE CHANNEL")
        with gr.Row():
            chat_input = gr.Textbox(
                label="Transmission",
                placeholder="Type when connected...",
                lines=2,
                scale=4,
                interactive=False,
            )
            send_btn = gr.Button("TRANSMIT", scale=1, interactive=False)

        with gr.Row():
            disconnect_btn = gr.Button("DISCONNECT", scale=1, interactive=False)
            chat_reply = gr.Textbox(label="◈ LAST RESPONSE", interactive=False, lines=2, scale=3)

    # Timer refresh
    timer = gr.Timer(value=3)

    timer.tick(
        fn=refresh_display,
        outputs=[thought_terminal, art_display, status_bar, stats_bar, send_btn, disconnect_btn, chat_input],
    )

    request_btn.click(
        fn=request_access,
        inputs=[reason_input],
        outputs=[request_status, thought_terminal, art_display, status_bar, stats_bar, send_btn, disconnect_btn, chat_input],
    )

    send_btn.click(
        fn=send_message,
        inputs=[chat_input],
        outputs=[chat_reply, thought_terminal, art_display, status_bar, stats_bar, send_btn, disconnect_btn, chat_input],
    ).then(
        fn=lambda: "",
        outputs=[chat_input],
    )

    disconnect_btn.click(
        fn=disconnect,
        outputs=[request_status, thought_terminal, art_display, status_bar, stats_bar, send_btn, disconnect_btn, chat_input],
    )

    demo.load(
        fn=lambda: (gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False)),
        outputs=[send_btn, disconnect_btn, chat_input],
    )


if __name__ == "__main__":
    agent.start()
    demo.queue(default_concurrency_limit=4)
    demo.launch()
