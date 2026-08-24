from __future__ import annotations

import json
from typing import Callable
from fastapi import Header
from pydantic import BaseModel, Field


class GameUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=4000)
    genre: str | None = Field(default=None, max_length=40)
    tags: list[str] | None = None
    visibility: str | None = None
    web3_enabled: bool | None = None


def register_game_edit_routes(app, *, db, session_user: Callable, audit: Callable, fail: Callable, now: Callable):
    @app.put('/api/v1/creator/games/{game_id}')
    def update_game(game_id: str, body: GameUpdateIn, authorization: str | None = Header(default=None)):
        user, _ = session_user(authorization)
        game = db.one('SELECT * FROM games WHERE game_id=? AND creator_id=?', (game_id, user['id']))
        if not game:
            fail('game_not_found', 'Game not found', 404)
        title = body.title.strip() if body.title is not None else game['title']
        description = body.description.strip() if body.description is not None else game['description']
        genre = body.genre.strip() if body.genre is not None else game['genre']
        tags_json = json.dumps((body.tags or [])[:12]) if body.tags is not None else game['tags_json']
        visibility = body.visibility.upper() if body.visibility is not None else game['visibility']
        if visibility not in {'PUBLIC', 'PRIVATE', 'UNLISTED'}:
            fail('invalid_visibility', 'Invalid visibility', 400)
        web3 = (1 if body.web3_enabled else 0) if body.web3_enabled is not None else game['web3_enabled']
        db.execute('UPDATE games SET title=?,description=?,genre=?,tags_json=?,visibility=?,web3_enabled=?,updated_at=? WHERE game_id=? AND creator_id=?',
                   (title, description, genre, tags_json, visibility, web3, now(), game_id, user['id']))
        audit(user['id'], 'game_updated', 'game', game_id)
        row = db.one('SELECT game_id,slug,title,description,genre,status,visibility,web3_enabled,created_at,updated_at FROM games WHERE game_id=?', (game_id,))
        return {'game': row}
