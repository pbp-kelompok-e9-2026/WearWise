from .models import ConditionRecord

Condition = ConditionRecord.Condition
Recommendation = ConditionRecord.Recommendation

RECOMMENDATION_BY_CONDITION = {
    Condition.GOOD: Recommendation.REUSE,
    Condition.MINOR: Recommendation.REPAIR,
    Condition.MAJOR: Recommendation.REPAIR,
    Condition.WORN_OUT: Recommendation.RECYCLE,
}


def recommend(condition):
    return RECOMMENDATION_BY_CONDITION.get(condition, Recommendation.REPAIR)