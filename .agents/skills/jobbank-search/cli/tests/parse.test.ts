import { describe, it, expect } from "bun:test"
import { parseRssDescription, extractJobIdFromUrl } from "../src/helpers.ts"

describe("parseRssDescription", () => {
  it("parses jobType, company, location, and a dated deadline", () => {
    const r = parseRssDescription(
      "Fuldtidsjob hos Novo Nordisk, København (Ansøgningsfrist: 31.12.2026)"
    )
    expect(r.jobType).toBe("Fuldtidsjob")
    expect(r.company).toBe("Novo Nordisk")
    expect(r.location).toBe("København")
    expect(r.deadline).toBe("31.12.2026")
  })

  it("returns null deadline for løbende (rolling)", () => {
    const r = parseRssDescription(
      "Praktikplads hos Vestas, Aarhus (Ansøgningsfrist: løbende)"
    )
    expect(r.deadline).toBeNull()
    expect(r.company).toBe("Vestas")
    expect(r.location).toBe("Aarhus")
  })

  it("falls back to full desc as company when ' hos ' is missing", () => {
    const r = parseRssDescription("Some unparsable string")
    expect(r.company).toBe("Some unparsable string")
    expect(r.jobType).toBe("")
    expect(r.location).toBe("")
  })

  it("keeps multiple job types before ' hos '", () => {
    const r = parseRssDescription(
      "Fuldtidsjob, Graduate/trainee hos Maersk, København (Ansøgningsfrist: 15.08.2026)"
    )
    expect(r.jobType).toBe("Fuldtidsjob, Graduate/trainee")
    expect(r.company).toBe("Maersk")
    expect(r.location).toBe("København")
  })
})

describe("extractJobIdFromUrl", () => {
  it("extracts the numeric job id from a jobbank URL", () => {
    expect(
      extractJobIdFromUrl("https://jobbank.dk/job/123456/novo-nordisk/some-title")
    ).toBe("123456")
  })

  it("returns empty string when no id is present", () => {
    expect(extractJobIdFromUrl("https://jobbank.dk/search")).toBe("")
  })
})
