class IncidentReported:
    def __init__(
        self,
        incident_id,
        game_copy_id,
        reported_by,
        incident_type,
        note,
        created_at,
    ):
        self.incident_id = incident_id
        self.game_copy_id = game_copy_id
        self.reported_by = reported_by
        self.incident_type = incident_type
        self.note = note
        self.created_at = created_at
