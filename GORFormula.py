from cmath import sqrt
# GOR Formula


def set_new_gor(r1, r2, user_level, actual):
    r1_expected = calc_expected(r2["rating"], r1["rating"])
    r2_expected = calc_expected(r1["rating"], r2["rating"])
    weight = calc_w(r1, r2)
    user_weight = 1 + (user_level/25)

    r1_gor = r1["rating"] + (weight*user_weight*(actual - r1_expected))
    r2_gor = r2["rating"] + (weight*user_weight * (0 - r2_expected)
                             ) if actual == 1 else r2["rating"] + (weight*user_weight * (1 - r2_expected))
    return [r1_gor, r2_gor]


def calc_w(r1, r2):
    distance = 1/(sqrt(pow((r2["long"] - r1["long"]),
                           2) + pow((r2["lat"] - r1["lat"]), 2)))

    cost = 1 - (abs((1/(1+pow(10, (r1["cost"]-r2["cost"]/3)))
                     ) - (1/(1+pow(10, (r2["cost"]-r1["cost"]/3))))))
    types = len(r1["types"].intersection(r2["types"]))
    return distance+cost+types


def calc_expected(r1_rank, r2_rank):
    return 1.0 / (1 + pow(10, ((r1_rank - r2_rank)/400)))


r1 = {
    "rating": 340,
    "lat": 33.15,
    "long": -115.12,
    "cost": 2,
    "types": {
        13000, 13050, 13001
    }
}

r2 = {
    "rating": 330,
    "lat": 33.18,
    "long": -115.30,
    "cost": 1,
    "types": {
        13000, 13050
    }
}

user = {
    "level": 25,
    "name": "Jake Speyer"
}

# 1 if r1 won 0 if r2 won
print(r1["rating"])
print(r2["rating"])
results = set_new_gor(r1, r2, user["level"], 1)
r1["rating"] = results[0]
r2["rating"] = results[1]
print("-------------")
print(r1["rating"])
print(r2["rating"])
