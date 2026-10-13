#!/usr/bin/env python3
"""Build the Hadestown cast-track timeline from the local data files."""

import json
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"


def main():
    performances = json.loads((DATA / "performances.json").read_text())
    cast = json.loads((DATA / "cast.json").read_text())
    headshots = json.loads((DATA / "headshots.json").read_text())

    performances = [
        p for p in performances
        if p.get("datetime") and p.get("date_match") is not False
    ]
    performances.sort(key=lambda p: p["datetime"])
    max_unassigned = {}
    for role in cast["roles"]:
        if role["tracks"] <= 1:
            continue
        rid = role["id"]
        maximum = 0
        for performance in performances:
            if performance.get("date_match") is False:
                continue
            changes = performance.get("changes", [])
            incoming = [
                change for change in changes
                if cast["role_aliases"].get(change["role"], change["role"].lower()) == rid
            ]
            changed_people = {change["performer"] for change in changes}
            departures = [
                person for person in role["principals"]
                if person in changed_people
                and cast["performers"].get(person, {}).get("home") == rid
            ]
            if incoming and not (len(incoming) == 1 and len(departures) == 1):
                maximum = max(maximum, len(incoming))
        max_unassigned[rid] = maximum

    payload = {
        "roles": cast["roles"],
        "roleAliases": cast["role_aliases"],
        "performers": cast["performers"],
        "headshots": headshots,
        "performances": performances,
        "maxUnassigned": max_unassigned,
    }

    (ROOT / "index.html").write_text(TEMPLATE.replace("__DATA__", json.dumps(payload)))
    print("wrote index.html")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hadestown Cast Changes</title>
<style>
  :root {
    --ink: #eee4d5;
    --muted: #a99b86;
    --gold: #d5ab55;
    --blue: #6baee8;
    --night: #15110e;
    --rail: #1c1713;
    --line: #352a20;
    --label-width: 202px;
    --column-width: 124px;
    --headshot-size: 70px;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--night);
    color: var(--ink);
    font-family: "Futura", "Avenir Next", "Helvetica Neue", sans-serif;
  }
  header { padding: 22px 24px 16px; }
  h1 {
    margin: 0;
    color: var(--gold);
    font-size: 20px;
    font-weight: 600;
    letter-spacing: .07em;
    text-transform: uppercase;
  }
  .sub { margin-top: 6px; color: var(--muted); font-size: 12px; }
  #date-sticky {
    position: sticky;
    top: 0;
    z-index: 8;
    display: flex;
    height: 54px;
    border-top: 1px solid var(--line);
    border-bottom: 1px solid #51402b;
    background: var(--rail);
  }
  #date-rail {
    display: flex;
    flex: 0 0 var(--label-width);
    align-items: center;
    width: var(--label-width);
    padding-left: 16px;
    border-right: 1px solid #51402b;
    box-shadow: 8px 0 18px rgb(0 0 0 / 24%);
    color: var(--muted);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .1em;
    text-transform: uppercase;
  }
  #date-wrap { flex: 1 1 auto; min-width: 0; overflow: hidden; }
  #date-stage { position: relative; height: 54px; }
  #layout { display: flex; align-items: flex-start; }
  #rail {
    position: sticky;
    left: 0;
    z-index: 4;
    flex: 0 0 var(--label-width);
    width: var(--label-width);
    background: var(--rail);
    border-right: 1px solid #51402b;
    box-shadow: 8px 0 18px rgb(0 0 0 / 24%);
  }
  #rail-stage, #stage { position: relative; }
  #wrap { flex: 1 1 auto; min-width: 0; overflow-x: auto; }
  .row-label {
    position: absolute;
    left: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 8px 12px 8px 16px;
    border-bottom: 1px solid var(--line);
    background: var(--rail);
  }
  .row-label .role {
    color: var(--gold);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .11em;
    text-transform: uppercase;
  }
  .row-label .person {
    margin-top: 4px;
    color: var(--ink);
    font-size: 13px;
    line-height: 1.2;
  }
  .row-label.unassigned .person { color: var(--muted); font-style: italic; }
  .cell {
    position: absolute;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 7px;
    padding: 6px;
    border-bottom: 1px solid var(--line);
  }
  .cell.unassigned-workers {
    flex-direction: column;
    flex-wrap: nowrap;
    justify-content: flex-start;
    padding-top: 8px;
    padding-bottom: 8px;
  }
  .chip {
    position: relative;
    flex: 0 0 var(--headshot-size);
    width: var(--headshot-size);
    height: var(--headshot-size);
    border-radius: 50%;
  }
  .chip img {
    display: block;
    width: 100%;
    height: 100%;
    border: 2px solid #76664d;
    border-radius: 50%;
    object-fit: cover;
    filter: brightness(.48) saturate(.65);
  }
  .chip.sub img {
    border: 3px solid var(--gold);
    filter: none;
  }
  .chip.swing img { border: 3px dashed var(--blue); }
  .chip .nm {
    position: absolute;
    z-index: 5;
    top: calc(100% + 3px);
    left: 50%;
    display: none;
    transform: translateX(-50%);
    padding: 4px 6px;
    border: 1px solid var(--line);
    border-radius: 3px;
    background: #211a14;
    color: var(--ink);
    font-size: 10px;
    white-space: nowrap;
  }
  .chip:hover .nm { display: block; }
  .colhead {
    position: absolute;
    top: 0;
    height: 54px;
    padding-top: 11px;
    border-left: 1px solid var(--line);
    color: var(--muted);
    font-size: 10px;
    line-height: 1.35;
    text-align: center;
  }
  .colhead .date { color: var(--ink); font-size: 11px; font-weight: 700; }
  .colhead.eve .date { color: var(--gold); }
  .nodata {
    position: absolute;
    z-index: 2;
    top: 0;
    bottom: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgb(21 17 14 / 80%);
    color: #756956;
    font-size: 11px;
    font-style: italic;
    pointer-events: none;
  }
  #arrows { position: absolute; inset: 0 auto auto 0; pointer-events: none; }
  .legend {
    padding: 14px 24px 22px;
    color: var(--muted);
    font-size: 11px;
    line-height: 1.7;
  }
  .legend b { color: var(--gold); }
  .legend b.blue { color: var(--blue); }
  @media (max-width: 640px) {
    :root { --label-width: 168px; --column-width: 112px; --headshot-size: 62px; }
    header { padding: 18px 16px 14px; }
    h1 { font-size: 17px; }
    .row-label { padding-left: 10px; }
    .row-label .person { font-size: 12px; }
    .legend { padding-right: 16px; padding-left: 16px; }
  }
</style>
</head>
<body>
<header>
  <h1>Hadestown &mdash; At This Performance</h1>
  <div class="sub">Each cast track has its own row. Scroll through dates; arrows trace the same-performance cover chain. Data updates daily at 1:30 PM and 6:30 PM Eastern.</div>
</header>
<div id="date-sticky" aria-label="Performance dates">
  <div id="date-rail">Cast track</div>
  <div id="date-wrap"><div id="date-stage"></div></div>
</div>
<main id="layout">
  <aside id="rail" aria-label="Cast tracks"><div id="rail-stage"></div></aside>
  <div id="wrap" aria-label="Performance timeline"><div id="stage"></div></div>
</main>
<div class="legend">
  <b>Gold ring</b> = substitute &nbsp;&middot;&nbsp;
  arrows connect a cast member moving to another role with the person covering their home track
  &nbsp;&middot;&nbsp; <b class="blue">Blue dashed outline</b> = a swing is coming in.
  Fate and Worker covers are placed in a named track only when the source data identifies that track;
  otherwise they appear in an unassigned row. Worker covers use the supplied femme/masc track groups.
</div>
<script>
const DATA = __DATA__;
const ALIAS = DATA.roleAliases;
const ROLE_BY_ID = Object.fromEntries(DATA.roles.map(role => [role.id, role]));
const LABELW = 202;
const COLW = 124;
const HEADER_H = 54;
const RIGHT_MARGIN = 40;
const DEFAULT_ROW_H = 100;
const UNKNOWN_ROW_H = 158;
const UNKNOWN_ITEM_H = 78;
const CHIP_RADIUS = parseFloat(
  getComputedStyle(document.documentElement).getPropertyValue("--headshot-size")
) / 2;
const roleId = name => ALIAS[name] || name.toLowerCase();
const home = person => (DATA.performers[person] || {}).home || "swing";
const workerGroup = person => (DATA.performers[person] || {}).worker_slot_group || "unknown";
const headshot = person => DATA.headshots[person] || "";
const slug = value => value.toLowerCase().replace(/[^a-z0-9]+/g, "-");
const performances = DATA.performances;

const rows = [];
const roleTracks = {};
const personTrack = {};
for (const role of DATA.roles) {
  const tracks = [];
  if (role.tracks > 1) {
    for (const person of role.principals) {
      const row = {
        id: `${role.id}-${slug(person)}`,
        roleId: role.id,
        roleName: role.name,
        person,
        label: person,
        unassigned: false,
        workerGroup: role.id === "workers" ? workerGroup(person) : null,
        height: DEFAULT_ROW_H
      };
      rows.push(row);
      tracks.push(row);
      personTrack[person] = row;
    }
    const unknown = {
      id: `${role.id}-unassigned`,
      roleId: role.id,
      roleName: role.name,
      person: null,
      label: "Track not identified",
      unassigned: true,
      height: Math.max(
        role.id === "workers" ? DEFAULT_ROW_H : UNKNOWN_ROW_H,
        16 + (DATA.maxUnassigned[role.id] || 0) * UNKNOWN_ITEM_H
      )
    };
    rows.push(unknown);
    tracks.push(unknown);
  } else {
    const person = role.principals[0];
    const row = {
      id: role.id,
      roleId: role.id,
      roleName: role.name,
      person,
      label: person,
      unassigned: false,
      height: DEFAULT_ROW_H
    };
    rows.push(row);
    tracks.push(row);
    personTrack[person] = row;
  }
  roleTracks[role.id] = tracks;
}

const rowTop = {};
let stageHeight = 0;
for (const row of rows) {
  rowTop[row.id] = stageHeight;
  stageHeight += row.height;
}
const stageWidth = performances.length * COLW;
const scrollWidth = stageWidth + RIGHT_MARGIN;
const stage = document.getElementById("stage");
const rail = document.getElementById("rail-stage");
const dateStage = document.getElementById("date-stage");
const timelineWrap = document.getElementById("wrap");
stage.style.width = `${scrollWidth}px`;
stage.style.height = `${stageHeight}px`;
rail.style.height = `${stageHeight}px`;
rail.style.width = `${LABELW}px`;
dateStage.style.width = `${stageWidth}px`;
document.getElementById("date-rail").style.width = `${LABELW}px`;
const syncDateHeader = () => {
  dateStage.style.transform = `translateX(${-timelineWrap.scrollLeft}px)`;
};
timelineWrap.addEventListener("scroll", syncDateHeader, { passive: true });
for (const row of rows) {
  const label = document.createElement("div");
  label.className = "row-label" + (row.unassigned ? " unassigned" : "");
  label.style.top = `${rowTop[row.id]}px`;
  label.style.width = `${LABELW}px`;
  label.style.height = `${row.height}px`;
  label.innerHTML = `<span class="role">${row.roleName}</span><span class="person"></span>`;
  label.querySelector(".person").textContent = row.label;
  rail.appendChild(label);
}

const SVG_NS = "http://www.w3.org/2000/svg";
const svg = document.createElementNS(SVG_NS, "svg");
svg.id = "arrows";
svg.setAttribute("width", stageWidth);
svg.setAttribute("height", stageHeight);
stage.appendChild(svg);
const defs = document.createElementNS(SVG_NS, "defs");
defs.innerHTML = `<marker id="arrowhead" markerWidth="8" markerHeight="8" refX="6.5" refY="4"
  orient="auto" markerUnits="strokeWidth"><path d="M0,0 L7,4 L0,8 Z" fill="#d5ab55"/></marker>`;
svg.appendChild(defs);

function makeChip(person, isSub, description) {
  const chip = document.createElement("div");
  const isSwing = isSub && home(person) === "swing";
  chip.className = "chip" + (isSub ? " sub" : "") + (isSwing ? " swing" : "");
  chip.dataset.person = person;
  const image = document.createElement("img");
  image.src = headshot(person);
  image.alt = person;
  chip.appendChild(image);
  const name = document.createElement("span");
  name.className = "nm";
  name.textContent = description || person;
  chip.appendChild(name);
  return chip;
}

function drawArrow(fromX, fromY, toX, toY, laneX) {
  const path = document.createElementNS(SVG_NS, "path");
  const sourceX = fromX - CHIP_RADIUS - 1;
  // End before the photo; the SVG sits beneath chips in the stacking order.
  const targetX = toX - CHIP_RADIUS - 4;
  const direction = toY >= fromY ? 1 : -1;
  const turn = Math.min(18, Math.abs(toY - fromY) / 3);
  const d = `M${sourceX},${fromY}
    C${laneX},${fromY} ${laneX},${fromY} ${laneX},${fromY + direction * turn}
    L${laneX},${toY - direction * turn}
    C${laneX},${toY} ${(laneX + targetX) / 2},${toY} ${targetX},${toY}`;
  path.setAttribute("d", d);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "#d5ab55");
  path.setAttribute("stroke-width", "1.8");
  path.setAttribute("marker-end", "url(#arrowhead)");
  path.setAttribute("opacity", ".9");
  svg.appendChild(path);
}

function centerInStage(element) {
  const box = element.getBoundingClientRect();
  const stageBox = stage.getBoundingClientRect();
  return {
    x: box.left - stageBox.left + box.width / 2,
    y: box.top - stageBox.top + box.height / 2
  };
}

const chipByAppearance = new Map();
const cellByTrack = new Map();
const displacedByCover = new Map();
const vacantSlotMoves = new Set();

performances.forEach((performance, column) => {
  const x = column * COLW;
  const dt = new Date(performance.datetime);
  const isMatinee = dt.getHours() < 17;
  const heading = document.createElement("div");
  heading.className = "colhead" + (isMatinee ? "" : " eve");
  heading.style.left = `${x}px`;
  heading.style.width = `${COLW}px`;
  heading.innerHTML = `<div class="date">${dt.toLocaleString("en", { month: "short" })} ${dt.getDate()}</div>
    <div>${isMatinee ? "matinee" : "evening"}</div>`;
  dateStage.appendChild(heading);

  const changes = performance.changes || [];
  const changesByRole = {};
  const changeByPerson = new Map();
  for (const change of changes) {
    const rid = roleId(change.role);
    (changesByRole[rid] ||= []).push(change);
    changeByPerson.set(change.performer, { ...change, roleId: rid });
  }

  const rowAssignments = new Map();
  for (const role of DATA.roles) {
    const rid = role.id;
    const roleChanges = changesByRole[rid] || [];
    const tracks = roleTracks[rid];
    if (role.tracks === 1) {
      if (roleChanges.length) rowAssignments.set(tracks[0].id, roleChanges);
      continue;
    }

    const knownDepartures = role.principals.filter(person =>
      changeByPerson.has(person) && home(person) === rid);
    const remainingChanges = [...roleChanges];
    const remainingDepartures = [...knownDepartures];

    for (const change of [...remainingChanges]) {
      const preferred = (DATA.performers[change.performer] || {}).preferred_track;
      const preferredRow = preferred && personTrack[preferred];
      if (!preferredRow || rowAssignments.has(preferredRow.id)) continue;
      if (rid === "workers" && workerGroup(change.performer) !== workerGroup(preferred)) continue;
      const preferredIsAway = remainingDepartures.includes(preferred);
      const incomingCount = rid === "workers"
        ? remainingChanges.filter(item => workerGroup(item.performer) === workerGroup(change.performer)).length
        : remainingChanges.length;
      const departureCount = rid === "workers"
        ? remainingDepartures.filter(person => workerGroup(person) === workerGroup(change.performer)).length
        : remainingDepartures.length;
      const unexplainedVacancy = incomingCount > departureCount;
      if (!preferredIsAway && (changeByPerson.has(preferred) || !unexplainedVacancy)) continue;

      rowAssignments.set(preferredRow.id, [change]);
      remainingChanges.splice(remainingChanges.indexOf(change), 1);
      if (preferredIsAway) {
        remainingDepartures.splice(remainingDepartures.indexOf(preferred), 1);
        displacedByCover.set(`${column}|${preferred}`, [change.performer]);
      }
    }

    if (rid === "workers") {
      for (const group of ["femme", "masc"]) {
        const groupChanges = remainingChanges.filter(change => workerGroup(change.performer) === group);
        const groupDepartures = remainingDepartures.filter(person => workerGroup(person) === group);
        if (groupChanges.length === 1 && groupDepartures.length === 1) {
          const displaced = groupDepartures[0];
          rowAssignments.set(personTrack[displaced].id, [groupChanges[0]]);
          displacedByCover.set(`${column}|${displaced}`, [groupChanges[0].performer]);
          remainingChanges.splice(remainingChanges.indexOf(groupChanges[0]), 1);
          remainingDepartures.splice(remainingDepartures.indexOf(displaced), 1);
        }
      }

      const unknownChanges = ["femme", "masc", "unknown"].flatMap(group =>
        remainingChanges.filter(change => workerGroup(change.performer) === group)
      );
      if (unknownChanges.length) {
        rowAssignments.set(`${rid}-unassigned`, unknownChanges);
      }
      for (const group of ["femme", "masc", "unknown"]) {
        const groupChanges = remainingChanges.filter(change => workerGroup(change.performer) === group);
        const groupDepartures = remainingDepartures.filter(person => workerGroup(person) === group);
        if (groupChanges.length && groupDepartures.length === 1) {
          vacantSlotMoves.add(`${column}|${groupDepartures[0]}`);
        }
      }
    } else if (remainingChanges.length === 1 && remainingDepartures.length === 1) {
      const displaced = remainingDepartures[0];
      rowAssignments.set(personTrack[displaced].id, remainingChanges);
      displacedByCover.set(`${column}|${displaced}`, [remainingChanges[0].performer]);
    } else if (remainingChanges.length) {
      rowAssignments.set(`${rid}-unassigned`, remainingChanges);
      if (remainingDepartures.length === 1) {
        vacantSlotMoves.add(`${column}|${remainingDepartures[0]}`);
      }
    }
  }

  for (const row of rows) {
    const cell = document.createElement("div");
    cell.className = "cell";
    if (row.unassigned && row.roleId === "workers") {
      cell.classList.add("unassigned-workers");
    }
    cell.style.left = `${x}px`;
    cell.style.top = `${rowTop[row.id]}px`;
    cell.style.width = `${COLW}px`;
    cell.style.height = `${row.height}px`;
    stage.appendChild(cell);
    cellByTrack.set(`${column}|${row.id}`, cell);

    if (performance.date_match === false) continue;

    const assigned = rowAssignments.get(row.id) || [];
    let occupants = assigned.map(change => ({ person: change.performer, sub: true }));
    if (!assigned.length && !row.unassigned && row.person && !changeByPerson.has(row.person)) {
      occupants = [{ person: row.person, sub: false }];
    }
    for (const occupant of occupants) {
      const change = changeByPerson.get(occupant.person);
      const source = home(occupant.person);
      const destination = change ? ROLE_BY_ID[change.roleId].name : row.roleName;
      const chip = makeChip(occupant.person, occupant.sub,
        `${occupant.person} — ${occupant.sub ? `${source === "swing" ? "swing" : `from ${ROLE_BY_ID[source]?.name || source}`} → ${destination}` : destination}`);
      cell.appendChild(chip);
      chipByAppearance.set(`${column}|${occupant.person}`, chip);
    }
  }

  if (performance.date_match === false) {
    const expired = document.createElement("div");
    expired.className = "nodata";
    expired.style.left = `${x}px`;
    expired.style.width = `${COLW}px`;
    expired.textContent = "data expired";
    stage.appendChild(expired);
  }
});

// Arrows follow a performer from their home track toward the role they cover.
const arrows = [];
for (const [key, covers] of displacedByCover) {
  const [column, displaced] = key.split("|");
  const movingChip = chipByAppearance.get(`${column}|${displaced}`);
  if (!movingChip) continue;
  for (const cover of covers) {
    const coverChip = chipByAppearance.get(`${column}|${cover}`);
    if (!coverChip) continue;
    arrows.push({
      column: Number(column),
      from: centerInStage(coverChip),
      to: centerInStage(movingChip)
    });
  }
}
for (const key of vacantSlotMoves) {
  const [column, displaced] = key.split("|");
  const vacancyCell = cellByTrack.get(`${column}|${personTrack[displaced]?.id}`);
  const movedChip = chipByAppearance.get(`${column}|${displaced}`);
  if (!vacancyCell || !movedChip) continue;
  arrows.push({
    column: Number(column),
    from: centerInStage(vacancyCell),
    to: centerInStage(movedChip)
  });
}

const arrowsByColumn = new Map();
for (const arrow of arrows) {
  if (!arrowsByColumn.has(arrow.column)) arrowsByColumn.set(arrow.column, []);
  arrowsByColumn.get(arrow.column).push(arrow);
}
for (const [column, columnArrows] of arrowsByColumn) {
  const x = column * COLW;
  const low = x + (column === 0 ? 3 : -23);
  const high = x + 17;
  const spacing = columnArrows.length > 1
    ? Math.min(8, (high - low) / (columnArrows.length - 1))
    : 8;
  const span = spacing * (columnArrows.length - 1);
  const start = Math.max(low, Math.min(x - 3 - span / 2, high - span));
  columnArrows.forEach((arrow, index) => {
    drawArrow(
      arrow.from.x,
      arrow.from.y,
      arrow.to.x,
      arrow.to.y,
      start + spacing * index
    );
  });
}

requestAnimationFrame(() => {
  timelineWrap.scrollLeft = timelineWrap.scrollWidth - timelineWrap.clientWidth;
  syncDateHeader();
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
