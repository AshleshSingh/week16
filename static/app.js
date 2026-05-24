const app = document.getElementById("app");

let token = null;
let user = null;

const api = async (path, options = {}) => {

  let url = path;

  if (
    token &&
    !path.includes("/login") &&
    !path.includes("/availability") &&
    !path.includes("/booking-request")
  ) {

    const separator = path.includes("?") ? "&" : "?";

    url = `${path}${separator}token=${encodeURIComponent(token)}`;
  }

  console.log("API CALL:", url);

  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json"
    },
    ...options
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text);
  }

  return res.json();
};

function eventHtml(e) {

  return `
    <div class="event">
      <span class="dot" style="background:${e.color}"></span>

      <div>
        <b>${e.title}</b>

        <p class="muted">
          ${e.category} ·
          ${new Date(e.start_time).toLocaleString()} ·
          ${e.priority}
        </p>

        <p>${e.notes ? e.notes : ""}</p>

        <button class="btn secondary" onclick="deleteEvent(${e.id})">
          Delete
        </button>
      </div>
    </div>
  `;
}

async function dashboard() {

  if (!token) {
    throw new Error("Token missing before dashboard load");
  }

  const events = await api("/api/events");

  const requests = await api("/api/booking-requests");

  app.innerHTML = `
    <section class="shell">

      <div class="topbar">

        <div class="brand">
          <h1>AI Scheduler OS</h1>

          <p>
            ${user.name}
            · Intelligent scheduling command center
          </p>
        </div>

        <div>
          <button class="btn secondary" onclick="availabilityView()">
            Availability
          </button>

          <button class="btn secondary" onclick="guestView()">
            Guest Portal
          </button>
        </div>

      </div>

      <div class="tabs">

        <button class="btn" onclick="dashboard()">
          Dashboard
        </button>

        <button class="btn secondary" onclick="ingestView()">
          Ingest Center
        </button>

        <button class="btn secondary" onclick="chatView()">
          AI Assistant
        </button>

      </div>

      <div class="cards">

        <div class="card">
          <h3>${events.length}</h3>
          <p class="muted">Scheduled Events</p>
        </div>

        <div class="card">
          <h3>${requests.length}</h3>
          <p class="muted">Guest Requests</p>
        </div>

        <div class="card">
          <h3>AI Active</h3>
          <p class="muted">Scheduler Intelligence Online</p>
        </div>

      </div>

      <div class="grid">

        <div class="panel">

          <h2>Upcoming Events</h2>

          ${
            events.length
            ? events.map(eventHtml).join("")
            : "<p class='muted'>No events available.</p>"
          }

        </div>

        <div class="panel">

          <h2>Guest Requests</h2>

          ${
            requests.length
            ? requests.map(r => `
              <div class="event">

                <div>

                  <b>${r.guest_name}</b>

                  <p class="muted">
                    ${new Date(r.requested_start).toLocaleString()}
                    · ${r.status}
                  </p>

                  <p>${r.purpose}</p>

                </div>

              </div>
            `).join("")
            : "<p class='muted'>No guest requests.</p>"
          }

        </div>

      </div>

    </section>
  `;
}

async function deleteEvent(id) {

  await api(`/api/events/${id}`, {
    method: "DELETE"
  });

  await dashboard();
}

function ingestView() {

  app.innerHTML = `
    <section class="shell">

      <div class="topbar">

        <div class="brand">
          <h1>Ingest Center</h1>

          <p>
            Paste email, PDF text, or handwritten note transcription.
          </p>
        </div>

        <button class="btn secondary" onclick="dashboard()">
          Back
        </button>

      </div>

      <div class="panel">

        <select id="source" class="input">

          <option>Email</option>
          <option>PDF</option>
          <option>Handwritten Note</option>
          <option>Manual Text</option>

        </select>

        <textarea id="content">
Subject: Client architecture review tomorrow at 2pm. Important discussion on AI scheduler prototype and Render deployment.
        </textarea>

        <button class="btn" onclick="ingest()">
          Extract + Create Event
        </button>

        <div id="result"></div>

      </div>

    </section>
  `;
}

async function ingest() {

  const data = await api("/api/ingest", {
    method: "POST",
    body: JSON.stringify({
      source_type: source.value,
      content: content.value
    })
  });

  result.innerHTML = `
    <div class="event">

      <div>

        <b>Created:</b> ${data.extracted.title}

        <p class="muted">
          Confidence:
          ${Math.round(data.extracted.confidence * 100)}%
        </p>

      </div>

    </div>
  `;
}

function chatView() {

  app.innerHTML = `
    <section class="shell">

      <div class="topbar">

        <div class="brand">
          <h1>AI Scheduling Assistant</h1>

          <p>
            Search, optimize, and manage your schedule.
          </p>
        </div>

        <button class="btn secondary" onclick="dashboard()">
          Back
        </button>

      </div>

      <div class="panel">

        <div class="chatbox" id="chatlog">

          <div class="msg">
            Ask me about availability, workload, or scheduling optimization.
          </div>

        </div>

        <input
          class="input"
          id="chatInput"
          value="Find my free slots tomorrow"
        />

        <button class="btn" onclick="sendChat()">
          Send
        </button>

      </div>

    </section>
  `;
}

async function sendChat() {

  const message = chatInput.value;

  chatlog.innerHTML += `
    <div class="msg user">${message}</div>
  `;

  const data = await api("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message })
  });

  chatlog.innerHTML += `
    <div class="msg">${data.reply}</div>
  `;
}

async function availabilityView() {

  const slots = await api("/api/availability");

  app.innerHTML = `
    <section class="shell">

      <div class="topbar">

        <div class="brand">
          <h1>Availability Projection</h1>

          <p>
            Guest-safe free/busy visibility.
          </p>
        </div>

        <button class="btn secondary" onclick="dashboard()">
          Back
        </button>

      </div>

      <div class="panel">

        <h2>Available Slots</h2>

        ${
          slots.slice(0, 18).map(s => `
            <div class="slot">

              <span>
                ${new Date(s.start).toLocaleString()}
              </span>

              <b class="${s.status}">
                ${s.status}
              </b>

            </div>
          `).join("")
        }

      </div>

    </section>
  `;
}

async function guestView() {

  const slots = await api("/api/availability");

  app.innerHTML = `
    <section class="shell">

      <div class="topbar">

        <div class="brand">
          <h1>Guest Booking Portal</h1>

          <p>
            Request availability blocks.
          </p>
        </div>

        <button class="btn secondary" onclick="dashboard()">
          Back
        </button>

      </div>

      <div class="grid">

        <div class="panel">

          <h2>Available Slots</h2>

          ${
            slots.slice(0, 18).map(s => `
              <div class="slot">

                <span>
                  ${new Date(s.start).toLocaleString()}
                </span>

                <b class="${s.status}">
                  ${s.status}
                </b>

              </div>
            `).join("")
          }

        </div>

        <div class="panel">

          <h2>Request a Block</h2>

          <input class="input" id="gname" placeholder="Your name"/>

          <input class="input" id="gemail" placeholder="Your email"/>

          <input class="input" id="gstart" type="datetime-local"/>

          <input class="input" id="gend" type="datetime-local"/>

          <textarea id="purpose" placeholder="Purpose"></textarea>

          <button class="btn" onclick="requestBlock()">
            Submit Request
          </button>

          <div id="guestResult"></div>

        </div>

      </div>

    </section>
  `;
}

async function requestBlock() {

  const data = await api("/api/booking-request", {
    method: "POST",
    body: JSON.stringify({
      guest_name: gname.value,
      guest_email: gemail.value,
      requested_start: new Date(gstart.value).toISOString(),
      requested_end: new Date(gend.value).toISOString(),
      purpose: purpose.value
    })
  });

  guestResult.innerHTML = `
    <p class="free">${data.message}</p>
  `;
}

async function initializeApp() {

  try {

    app.innerHTML = `
      <section class="shell">

        <div class="panel">

          <h2>Initializing AI Scheduler OS...</h2>

          <p class="muted">
            Loading intelligent scheduling environment.
          </p>

        </div>

      </section>
    `;

    const response = await fetch("/api/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        email: "ashlesh@example.com",
        password: "demo123"
      })
    });

    if (!response.ok) {
      throw new Error("Auto-login failed");
    }

    const data = await response.json();

    token = data.token;
    user = data.user;

    console.log("TOKEN:", token);

    await dashboard();

  } catch (err) {

    console.error(err);

    app.innerHTML = `
      <section class="shell">

        <div class="panel">

          <h2>Application Error</h2>

          <p class="muted">
            ${err.message}
          </p>

        </div>

      </section>
    `;
  }
}

initializeApp();