import { describe, test, expect } from "bun:test";
import { parseJobCards, parseJobDetail } from "../src/helpers";

// Minimal search-card markup: parseJobCards splits on the job-posting URN and
// needs an id, a base-search-card__title, and a full-link. Everything else is
// optional. We inject HTML entities into the title/company to exercise decoding.
function searchCard(id: string, title: string, company = "Acme"): string {
  return `<li>
    <div data-entity-urn="urn:li:jobPosting:${id}">
      <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/${id}"></a>
      <h3 class="base-search-card__title">${title}</h3>
      <h4 class="base-search-card__subtitle"><a href="https://www.linkedin.com/company/acme">${company}</a></h4>
    </div>
  </li>`;
}

describe("decodeHtmlEntities (via parseJobCards)", () => {
  test("decodes hexadecimal numeric entities (&#xE9;)", () => {
    const [card] = parseJobCards(searchCard("123", "Caf&#xE9; Manager"));
    expect(card.title).toBe("Café Manager");
  });

  test("decodes uppercase-X hexadecimal entities (&#X...;)", () => {
    const [card] = parseJobCards(searchCard("124", "Deb&#XFC;t Role")); // &#XFC; = ü
    expect(card.title).toBe("Debüt Role");
  });

  test("still decodes decimal numeric entities (&#233;) — regression", () => {
    const [card] = parseJobCards(searchCard("125", "Caf&#233; Lead"));
    expect(card.title).toBe("Café Lead");
  });

  test("decodes supplementary-plane code points with fromCodePoint (&#128512;)", () => {
    const [card] = parseJobCards(searchCard("126", "Growth &#128512;"));
    expect(card.title).toBe("Growth 😀");
  });

  test("decodes hex supplementary-plane code points (&#x1F600;)", () => {
    const [card] = parseJobCards(searchCard("127", "Growth &#x1F600;"));
    expect(card.title).toBe("Growth 😀");
  });

  test("decodes hex entities in the company subtitle too", () => {
    const [card] = parseJobCards(searchCard("128", "Engineer", "N&#xF8;rrebro ApS"));
    expect(card.company).toBe("Nørrebro ApS");
  });
});

describe("decodeHtmlEntities (via parseJobDetail)", () => {
  test("decodes hex entities inside the job title", () => {
    const html = `<h1 class="topcard__title">Se&#xF1;or Engineer</h1>`;
    const job = parseJobDetail(html, "999");
    expect(job.title).toBe("Señor Engineer");
  });
});

// Pins the empty-result contract that runSearch turns into a PARSER_EMPTY stderr
// warning: when LinkedIn's markup changes (login wall, anti-bot, redesign) the
// job-posting URN anchor disappears and parseJobCards must return [] — never
// throw. This guards the "silent empty" failure mode from regressing.
describe("parseJobCards empty-result contract (PARSER_EMPTY trigger)", () => {
  test("returns [] when the job-posting URN anchor is absent (login wall / markup change)", () => {
    const wall = `<html><body><div class="artdeco">Please sign in to view jobs</div></body></html>`;
    expect(parseJobCards(wall)).toEqual([]);
  });

  test("returns [] for a genuine no-results page with no cards", () => {
    const empty = `<section class="jobs-search__results-list"><p>No jobs found</p></section>`;
    expect(parseJobCards(empty)).toEqual([]);
  });

  test("still extracts a card when the anchor IS present", () => {
    const cards = parseJobCards(searchCard("777", "Real Job"));
    expect(cards).toHaveLength(1);
    expect(cards[0].id).toBe("777");
    expect(cards[0].title).toBe("Real Job");
  });
});
