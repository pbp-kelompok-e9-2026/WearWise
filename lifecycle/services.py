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

REPAIR_GUIDES = [
    {
        "recommendation": Recommendation.REPAIR,
        "title": "Repair",
        "summary": "Perbaiki kerusakan supaya pakaian bisa dipakai lagi.",
        "steps": [
            "Kancing lepas: jahit ulang dengan benang sewarna, ikat simpul di bagian dalam.",
            "Jahitan terbuka atau sobek kecil: jahit tusuk jelujur dari sisi dalam kain.",
            "Lubang kecil: tambal dengan kain sejenis atau iron-on patch.",
            "Resleting macet: gosok gigi resleting dengan lilin atau pensil grafit.",
            "Kerusakan besar: bawa ke penjahit terdekat.",
        ],
    },
    {
        "recommendation": Recommendation.REUSE,
        "title": "Reuse",
        "summary": "Pakaian masih layak, beri kesempatan dipakai lagi.",
        "steps": [
            "Padukan ulang dengan pakaian lain supaya lebih sering dipakai.",
            "Tukar dengan teman atau ikut acara swap pakaian.",
            "Jual sebagai preloved jika sudah jarang dipakai.",
            "Donasikan ke yayasan atau orang yang membutuhkan.",
        ],
    },
    {
        "recommendation": Recommendation.RECYCLE,
        "title": "Recycle",
        "summary": "Pakaian sudah tidak layak pakai, olah bahannya.",
        "steps": [
            "Potong menjadi kain lap atau kain pembersih.",
            "Gunakan sebagai bahan kerajinan, misalnya tas atau sarung bantal.",
            "Setor ke bank sampah atau drop box daur ulang tekstil.",
            "Pisahkan kancing dan resleting yang masih bisa dipakai lagi.",
        ],
    },
]