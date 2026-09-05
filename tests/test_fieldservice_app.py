from src.fieldservice_app import FollowUpRequest, WorkOrder, record_follow_up


def test_follow_up_records_photo_and_changes_dispatch_state():
    order = WorkOrder("wo-7", "12 Main", status="dispatched", technician_id="tech-2")
    result = record_follow_up(order, FollowUpRequest("tech-2", "Replaced valve", "before.jpg"))
    assert result.status == "follow_up"
    assert result.photos == ["before.jpg"]
    assert result.follow_up == "Replaced valve"
