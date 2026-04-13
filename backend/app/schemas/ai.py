"""
Pydantic v2 schemas for Claude AI responses.

FaceAnalysisResult  — parsed output from the Vision (관상) call
FortuneReadingResult — parsed output from the Text (운세) call

All models use ConfigDict(extra="ignore") so minor schema drift from
Claude's output does not crash validation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AxisScore(BaseModel):
    """One physiognomy axis score returned by the Vision model."""

    model_config = ConfigDict(extra="ignore")

    score: int = Field(..., ge=0, le=10, description="관상 점수 0~10")
    detail: str = Field(..., description="관상 분석 코멘트")


class FortuneAxis(BaseModel):
    """One fortune axis score returned by the Text model."""

    model_config = ConfigDict(extra="ignore")

    score: int = Field(..., ge=0, le=10, description="운세 점수 0~10")
    reading: str = Field(..., description="운세 풀이 코멘트")


class FaceAnalysisResult(BaseModel):
    """Full structured response from the Claude Vision 관상 call (README §4-1)."""

    model_config = ConfigDict(extra="ignore")

    pitcher_name: str
    command: AxisScore
    stuff: AxisScore
    composure: AxisScore
    dominance: AxisScore
    destiny: AxisScore
    overall_impression: str


class FortuneReadingResult(BaseModel):
    """Full structured response from the Claude Text 운세 call (README §4-2)."""

    model_config = ConfigDict(extra="ignore")

    pitcher_name: str
    date: str
    command_fortune: FortuneAxis
    stuff_fortune: FortuneAxis
    composure_fortune: FortuneAxis
    dominance_fortune: FortuneAxis
    destiny_fortune: FortuneAxis
    daily_summary: str
    lucky_inning: int = Field(..., ge=1, le=9, description="오늘의 행운 이닝 1~9")
