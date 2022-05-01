from sqlmodel import SQLModel, Field, Column, text
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.mysql import TIMESTAMP
from typing import Optional


class SubPositionLink(SQLModel, table=True):
    __tablename__ = 'sub_position_links'
    sub_position_id: Optional[int] = Field(
        default=None, foreign_key="sub_positions.id",
        primary_key=True, nullable=False,
    )
    position_flow_id: Optional[int] = Field(
        default=None, foreign_key="position_flows.id",
        primary_key=True, nullable=False,
    )

    @declared_attr
    def created_at(cls):
        return Column(
            TIMESTAMP(fsp=6), nullable=False,
            server_default=text("CURRENT_TIMESTAMP(6)")
        )

    @declared_attr
    def updated_at(cls):
        return Column(
            TIMESTAMP(fsp=6), nullable=False,
            server_default=text(
                "CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"
            ),
        )
