"""ORM models mirroring SPEC.md §7.

Prototype note: runs on SQLite (no Docker/Postgres on the dev machine). Differences
from the PostGIS target are deliberate and small so the swap is mechanical:
  * geom GEOGRAPHY(POINT)  -> lat/lon REAL columns (distance done with haversine)
  * TEXT[] / INT[]         -> JSON columns
  * passage.embedding      -> not stored; retrieval uses BM25 (see copilot/)
Additions (needed by real data): passage_id on event/action, mud_check table for
Sodir mud-weight-by-depth records, npt_hours on episode.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Field(Base):
    __tablename__ = "field"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    country: Mapped[str | None]
    source: Mapped[str | None]


class Well(Base):
    __tablename__ = "well"
    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String, unique=True, index=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    field_id: Mapped[int | None] = mapped_column(ForeignKey("field.id"))
    field_name: Mapped[str | None] = mapped_column(String, index=True)
    country: Mapped[str | None] = mapped_column(String, index=True)  # ISO-style English name, e.g. "India", "Norway"
    lat: Mapped[float | None] = mapped_column(Float, index=True)
    lon: Mapped[float | None] = mapped_column(Float, index=True)
    kb_elev_m: Mapped[float | None]
    water_depth_m: Mapped[float | None]
    spud_date: Mapped[date | None] = mapped_column(Date)
    td_md_m: Mapped[float | None]
    td_tvd_m: Mapped[float | None]
    status: Mapped[str | None]
    purpose: Mapped[str | None]
    well_type: Mapped[str | None]
    operator: Mapped[str | None]
    formation_at_td: Mapped[str | None]
    source: Mapped[str | None]
    position_source: Mapped[str | None]
    parent_well: Mapped[str | None]  # wellbores sharing a parent (sidetracks) are not independent
    external_id: Mapped[str | None]  # e.g. Sodir NPDID
    fact_url: Mapped[str | None]


class SurveyStation(Base):
    __tablename__ = "survey_station"
    id: Mapped[int] = mapped_column(primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("well.id"), index=True)
    md_m: Mapped[float]
    inc_deg: Mapped[float | None]
    azi_deg: Mapped[float | None]
    tvd_m: Mapped[float | None]
    north_m: Mapped[float | None]
    east_m: Mapped[float | None]


class FormationTop(Base):
    __tablename__ = "formation_top"
    id: Mapped[int] = mapped_column(primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("well.id"), index=True)
    formation: Mapped[str] = mapped_column(String, index=True)
    level: Mapped[str | None]  # FORMATION | GROUP | MEMBER
    grp: Mapped[str | None]
    lithology: Mapped[str | None]
    top_md_m: Mapped[float | None]
    top_tvd_m: Mapped[float | None]
    base_md_m: Mapped[float | None]
    source: Mapped[str | None]
    source_ref: Mapped[str | None]


class Document(Base):
    __tablename__ = "document"
    id: Mapped[int] = mapped_column(primary_key=True)
    well_id: Mapped[int | None] = mapped_column(ForeignKey("well.id"), index=True)
    kind: Mapped[str]  # WELL_HISTORY | DDR_PDF | DDR_XML | WCR_PDF | EOWR_PDF | MUDLOG | OTHER
    title: Mapped[str | None]
    path: Mapped[str | None]
    url: Mapped[str | None]
    report_date: Mapped[date | None] = mapped_column(Date)
    pages: Mapped[int | None]
    is_scanned: Mapped[bool | None] = mapped_column(Boolean)
    ocr_mean_conf: Mapped[float | None]
    sha256: Mapped[str | None] = mapped_column(String, unique=True)
    licence: Mapped[str | None]
    report_md_m: Mapped[float | None]  # depth printed on the report header (DDRs)
    country: Mapped[str | None] = mapped_column(String, index=True)  # set by engines.post.assign_countries


class Passage(Base):
    __tablename__ = "passage"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), index=True)
    well_id: Mapped[int | None] = mapped_column(ForeignKey("well.id"), index=True)
    locator: Mapped[str]  # e.g. "p3.s2" (paragraph/sentence) or "page 2, line 14"
    seq: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    md_m: Mapped[float | None]
    report_date: Mapped[date | None] = mapped_column(Date)


class Activity(Base):
    __tablename__ = "activity"
    id: Mapped[int] = mapped_column(primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("well.id"), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("document.id"))
    passage_id: Mapped[int | None] = mapped_column(ForeignKey("passage.id"))
    seq: Mapped[int | None]
    t_start: Mapped[datetime | None] = mapped_column(DateTime)
    t_end: Mapped[datetime | None] = mapped_column(DateTime)
    md_m: Mapped[float | None]
    tvd_m: Mapped[float | None]
    phase: Mapped[str | None]
    code: Mapped[str | None]
    state: Mapped[str | None]
    comment: Mapped[str | None] = mapped_column(Text)
    formation: Mapped[str | None]


class Event(Base):
    __tablename__ = "event"
    id: Mapped[int] = mapped_column(primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("well.id"), index=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activity.id"))
    passage_id: Mapped[int | None] = mapped_column(ForeignKey("passage.id"), index=True)
    hazard: Mapped[str] = mapped_column(String, index=True)
    md_m: Mapped[float | None]
    tvd_m: Mapped[float | None]
    formation: Mapped[str | None] = mapped_column(String, index=True)
    t: Mapped[datetime | None] = mapped_column(DateTime)
    severity: Mapped[str | None]
    quantity: Mapped[float | None]
    quantity_unit: Mapped[str | None]
    mud_weight_ppg: Mapped[float | None]
    mud_weight_source: Mapped[str | None]  # "text" | "sodir_mud_table"
    confidence: Mapped[float]
    method: Mapped[str]  # rule | llm | rule+llm | human
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_span: Mapped[str | None] = mapped_column(Text)
    source_ref: Mapped[str]


class Action(Base):
    __tablename__ = "action"
    id: Mapped[int] = mapped_column(primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("well.id"), index=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activity.id"))
    passage_id: Mapped[int | None] = mapped_column(ForeignKey("passage.id"))
    action_type: Mapped[str] = mapped_column(String, index=True)
    detail: Mapped[str | None] = mapped_column(Text)
    t: Mapped[datetime | None] = mapped_column(DateTime)
    md_m: Mapped[float | None]
    confidence: Mapped[float]
    source_ref: Mapped[str]


class Episode(Base):
    __tablename__ = "episode"
    id: Mapped[int] = mapped_column(primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("well.id"), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("event.id"))
    hazard: Mapped[str] = mapped_column(String, index=True)
    formation: Mapped[str | None] = mapped_column(String, index=True)
    md_m: Mapped[float | None]
    action_ids: Mapped[list] = mapped_column(JSON, default=list)
    action_types: Mapped[list] = mapped_column(JSON, default=list)
    outcome: Mapped[str]  # resolved | partial | unresolved | worsened | unknown
    outcome_ref: Mapped[str | None]
    outcome_text: Mapped[str | None] = mapped_column(Text)
    hours_to_resolve: Mapped[float | None]
    npt_hours: Mapped[float | None]  # lost time explicitly stated in the source
    confidence: Mapped[float]
    reviewed_by: Mapped[str | None]
    outcome_method: Mapped[str | None] = mapped_column(String, default="rule")  # rule | local_llm


class PressureTest(Base):
    __tablename__ = "pressure_test"
    id: Mapped[int] = mapped_column(primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("well.id"), index=True)
    kind: Mapped[str]  # LOT | FIT
    md_m: Mapped[float | None]
    tvd_m: Mapped[float | None]
    emw_ppg: Mapped[float]
    raw_value: Mapped[float | None]
    raw_unit: Mapped[str | None]
    casing_shoe_md_m: Mapped[float | None]
    formation: Mapped[str | None] = mapped_column(String, index=True)
    source_ref: Mapped[str]


class CasingString(Base):
    __tablename__ = "casing_string"
    id: Mapped[int] = mapped_column(primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("well.id"), index=True)
    casing_type: Mapped[str | None]
    od_in: Mapped[float | None]
    hole_in: Mapped[float | None]
    shoe_md_m: Mapped[float | None]
    shoe_tvd_m: Mapped[float | None]
    hole_md_m: Mapped[float | None]
    formation: Mapped[str | None]
    cement_top_md_m: Mapped[float | None]
    cement_issue: Mapped[str | None]
    source_ref: Mapped[str]


class MudCheck(Base):
    __tablename__ = "mud_check"
    id: Mapped[int] = mapped_column(primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("well.id"), index=True)
    md_m: Mapped[float]
    mw_ppg: Mapped[float]
    raw_value: Mapped[float]
    raw_unit: Mapped[str]
    mud_type: Mapped[str | None]
    measured: Mapped[date | None] = mapped_column(Date)
    source_ref: Mapped[str]


class RealtimeSample(Base):
    __tablename__ = "realtime_sample"
    id: Mapped[int] = mapped_column(primary_key=True)
    well_id: Mapped[int] = mapped_column(Integer, index=True)
    t: Mapped[datetime] = mapped_column(DateTime, index=True)
    md_m: Mapped[float | None]
    bit_md_m: Mapped[float | None]
    rop: Mapped[float | None]
    wob: Mapped[float | None]
    rpm: Mapped[float | None]
    torque: Mapped[float | None]
    spp: Mapped[float | None]
    flow_in: Mapped[float | None]
    pit_vol: Mapped[float | None]
    hookload: Mapped[float | None]
    mw_in_ppg: Mapped[float | None]


class AuditFlag(Base):
    __tablename__ = "audit_flag"
    id: Mapped[int] = mapped_column(primary_key=True)
    well_id: Mapped[int | None] = mapped_column(Integer, index=True)
    rule: Mapped[str]
    severity: Mapped[str]
    claim_a: Mapped[str] = mapped_column(Text)
    ref_a: Mapped[str]
    claim_b: Mapped[str] = mapped_column(Text)
    ref_b: Mapped[str]
    delta: Mapped[str | None]
    status: Mapped[str] = mapped_column(String, default="open")
    reviewer_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[str | None]


class WikiPage(Base):
    __tablename__ = "wiki_page"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True)
    kind: Mapped[str]
    title: Mapped[str]
    ref_no: Mapped[str]
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String, default="draft")
    git_commit: Mapped[str | None]
    approved_by: Mapped[str | None]
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    trust: Mapped[float | None]
    n_sources: Mapped[int | None]


class WikiNoting(Base):
    __tablename__ = "wiki_noting"
    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("wiki_page.id"), index=True)
    para_no: Mapped[int]
    author: Mapped[str]
    role: Mapped[str]
    note: Mapped[str] = mapped_column(Text)
    action: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    git_commit: Mapped[str | None]


class EvalResult(Base):
    __tablename__ = "eval_result"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    metric: Mapped[str]
    value: Mapped[float | None]
    n: Mapped[int | None]
    run_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)


class Basin(Base):
    """Indian sedimentary basin (NDR / DGH public summary page)."""
    __tablename__ = "basin"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    slug: Mapped[str] = mapped_column(String, unique=True)
    url: Mapped[str]
    category: Mapped[str | None]
    area_sqkm: Mapped[float | None]       # only when the page states a single area figure
    area_text: Mapped[str | None] = mapped_column(Text)  # verbatim sentence the area comes from
    exploratory_wells: Mapped[float | None]
    bbox: Mapped[list | None] = mapped_column(JSON)  # [minLon, minLat, maxLon, maxLat] parsed from the page text
    document_id: Mapped[int | None] = mapped_column(ForeignKey("document.id"))
    n_tables: Mapped[int | None]


class DataSource(Base):
    __tablename__ = "data_source"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    url: Mapped[str]
    licence: Mapped[str]
    records: Mapped[int]
    loaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)


class AlertFeedback(Base):
    """An engineer's verdict on an alert (self-correcting alerts). A "problem" verdict becomes a human-labelled
    record for that (well, layer, hazard): later estimates for OTHER wells learn from it. The Hindsight test never
    scores on these labels (it uses the written records only), so feedback cannot inflate the measured accuracy."""
    __tablename__ = "alert_feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("well.id"), index=True)
    formation: Mapped[str] = mapped_column(String, index=True)
    hazard: Mapped[str] = mapped_column(String, index=True)
    verdict: Mapped[str]            # problem | no_problem | unsure
    md_m: Mapped[float | None]
    note: Mapped[str | None] = mapped_column(Text)
    reviewer: Mapped[str]
    role: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
