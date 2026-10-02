"""Atria 正式引擎 — 世界模块
25 人镇: 40x30=1200 格 / 12 地点 / ~45 物品 / 25 出生点
每个地点一个矩形区域 + 物品列表。碰撞用格级通行表。
"""
import json

GRID_W, GRID_H = 40, 30

# 12 地点: 5 住宅 + 4 商铺 + 1 学校 + 1 公园 + 1 pub (方案 3.2)
PLACES = {
    # name: (x0,y0,x1,y1) 矩形, [物品], 出生点归属
    "安镇老宅":      dict(box=(2,2,7,6),    items=["床","书桌","冰箱","餐桌"],          home_of="安镇"),
    "周家小院":      dict(box=(10,2,15,6),  items=["床","书桌","餐桌","衣柜"],          home_of="周老师"),
    "赵宅":          dict(box=(18,2,23,6),  items=["床","药柜","书桌"],                 home_of="赵医生"),
    "孙氏裁缝铺":    dict(box=(26,2,31,6),  items=["缝纫机","布料架","镜子"],           home_of="孙裁缝"),
    "李家":          dict(box=(34,2,39,6),  items=["床","餐桌","收音机"],               home_of="李大姐"),
    "邮局":          dict(box=(2,10,7,15),  items=["柜台","包裹架","信箱","长椅"],      home_of=None),
    "五金店":        dict(box=(10,10,15,15),items=["工具架","柜台","钉子箱"],           home_of=None),
    "杂货铺":        dict(box=(18,10,23,15),items=["货架","柜台","蔬菜筐"],             home_of=None),
    "诊所":          dict(box=(26,10,31,15),items=["诊台","药柜","候诊椅"],             home_of=None),

    "镇学校":        dict(box=(2,20,7,25),  items=["黑板","课桌","讲台"],               home_of=None),
    "镇公园":        dict(box=(10,20,20,25),items=["长椅","喷泉","滑梯"],               home_of=None),
    "老磨坊酒吧":    dict(box=(26,20,31,25),items=["吧台","酒架","桌椅"],               home_of=None),
}

# 住宅区（南部 20 户，每户 2x2 小宅，供其余 20 人居住）
HOMES_SOUTH = {
    "孙有财宅": (2,28,3,29), "吴怀疑宅": (5,28,6,29), "郑大妈宅": (8,28,9,29),
    "王邮差宅": (11,28,12,29), "冯铁匠宅": (14,28,15,29), "陈寡妇宅": (17,28,18,29),
    "魏猎户宅": (20,28,21,29), "沈郎中宅": (23,28,24,29), "韩屠户宅": (26,28,27,29),
    "朱寡妇宅": (29,28,30,29), "秦木匠宅": (32,28,33,29), "尤老太宅": (35,28,36,29),
    "许货郎宅": (2,26,3,26), "何书生宅": (5,26,6,26), "吕婶宅": (8,26,9,26),
    "张石匠宅": (11,26,12,26), "郭船夫宅": (14,26,15,26), "马寡妇宅": (17,26,18,26),
    "段更夫宅": (20,26,21,26), "秦木匠宅2": (23,26,24,26),
}
# 别名（人设 living_area 与地图名对齐）
HOME_ALIAS = {"秦木匠宅2": "秦木匠宅"}

# 道路带（连通各地点，宽 2 格）
ROADS = {
    "北街": (2,7,39,8),       # 东西向, 连 5 住宅
    "中街": (2,16,39,17),     # 东西向, 连 4 商铺
    "南街": (2,26,39,27),     # 东西向, 连 学校/公园/酒吧
    "住宅南街": (1,29,39,29), # 南部住宅排
    "西大道": (8,2,9,27),     # 南北向
    "中大道": (16,2,17,27),
    "东大道": (24,2,25,27),
    "公园道": (21,20,22,25),  # 公园较宽, 单独道
}

class World:
    def __init__(self):
        self.w, self.h = GRID_W, GRID_H
        self.places = {}
        self.roads = set()
        self.item_at = {}     # "地点:物品" -> (x,y)
        self.spawn = {}       # agent -> (x,y)
        self._build()

    def _box_cells(self, box):
        x0,y0,x1,y1 = box
        return {(x,y) for x in range(x0,x1+1) for y in range(y0,y1+1)}

    def _build(self):
        # 道路全通行
        for name, box in ROADS.items():
            self.roads |= self._box_cells(box)
        # 南部住宅: 每户 2x2, 内部通行, 南墙开门
        for name, box in HOMES_SOUTH.items():
            x0,y0,x1,y1 = box
            inner = {(x,y) for x in range(x0,x1+1) for y in range(y0,y1+1)}
            self.places[name] = {"cells": inner, "items": ["床","餐桌"], "home_of": None}
            self.walkable_homes = getattr(self, "walkable_homes", set()) | inner
            # 南墙开门 (y=y1+1 即住宅南街)
            mx = (x0+x1)//2
            self.roads |= {(mx,y1+1)}
        # 地点: 外墙不通行, 内部通行
        walkable = set(self.roads) | getattr(self, "walkable_homes", set())
        for name, spec in PLACES.items():
            cells = self._box_cells(spec["box"])
            self.places[name] = {"cells": cells, "items": spec["items"], "home_of": spec["home_of"]}
            x0,y0,x1,y1 = spec["box"]
            inner = {(x,y) for x in range(x0+1,x1) for y in range(y0+1,y1)}
            walkable |= inner
            # 门的开口: 每个地点南墙留 2 格
            mx = (x0+x1)//2
            walkable |= {(mx,y1),(mx+1,y1)}
            walkable |= {(mx,y1+1),(mx+1,y1+1)}  # 门外接道路
            # 物品放地点内边沿
            for i, it in enumerate(spec["items"]):
                ix = x0+1+(i % max(1,(x1-x0-1)))
                iy = y0+1+(i // max(1,(x1-x0-1)))
                if (ix,iy) in inner or (ix,iy) in walkable:
                    self.item_at[f"{name}:{it}"] = (ix,iy)
        self.walkable = walkable
        # 出生点 = 各住宅/商铺中心
        for name, spec in PLACES.items():
            if spec["home_of"]:
                x0,y0,x1,y1 = spec["box"]
                self.spawn[spec["home_of"]] = ((x0+x1)//2,(y0+y1)//2)
        self.spawn["安镇老宅"] = self.spawn.get("安镇", (4,4))
        self.spawn["周家小院"] = self.spawn.get("周老师", (12,4))
        self.spawn["赵宅"] = self.spawn.get("赵医生", (20,4))
        self.spawn["李家"] = self.spawn.get("李大姐", (36,4))
        self.spawn["孙氏裁缝铺"] = self.spawn.get("孙裁缝", (28,4))
        # 南部住宅出生点
        for name, box in HOMES_SOUTH.items():
            x0,y0,x1,y1 = box
            self.spawn[HOME_ALIAS.get(name, name)] = ((x0+x1)//2,(y0+y1)//2)
        # 别名对齐: 人设里的 living_area
        self.spawn["老磨坊酒吧"] = self.spawn.get("老磨坊酒吧", (28,22))
        self.spawn["吴怀疑"] = self.spawn.get("吴怀疑宅", (5,28))
        self.spawn["郑大妈"] = self.spawn.get("郑大妈宅", (8,28))
        self.spawn["钱老板"] = self.spawn.get("老磨坊酒吧", (28,22))

    def place_of(self, x, y):
        for name, spec in self.places.items():
            if (x,y) in spec["cells"]:
                return name
        for rname, box in ROADS.items():
            x0,y0,x1,y1 = box
            if x0<=x<=x1 and y0<=y<=y1:
                return rname
        return "郊外"

    def is_walkable(self, x, y):
        return 0<=x<self.w and 0<=y<self.h and (x,y) in self.walkable

    def items_near(self, place):
        return [k for k in self.item_at if k.startswith(place+":")]

    defToJson = None
    def to_json(self):
        return {"w":self.w,"h":self.h,
                "places":{k:{"box":PLACES[k]["box"],"items":PLACES[k]["items"],"home_of":PLACES[k]["home_of"]} for k in PLACES},
                "homes_south":HOMES_SOUTH,
                "roads":{k:v for k,v in ROADS.items()},
                "item_at":self.item_at,"spawn":self.spawn}

if __name__ == "__main__":
    w = World()
    cells = w.w*w.h
    wk = len(w.walkable)
    print(f"地图 {w.w}x{w.h} = {cells} 格")
    print(f"通行 {wk} 格 / 阻挡 {cells-wk} 格 ({(cells-wk)/cells*100:.1f}%)")
    print(f"地点 {len(w.places)} 个, 物品 {len(w.item_at)} 个, 出生点 {len(w.spawn)} 个")
    print("出生点:", w.spawn)
    # 连通性检查: BFS 从每个出生点能否到所有地点
    from collections import deque
    def reach(sx,sy):
        seen={(sx,sy)}; q=deque([(sx,sy)])
        while q:
            x,y=q.popleft()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx,ny=x+dx,y+dy
                if w.is_walkable(nx,ny) and (nx,ny) not in seen:
                    seen.add((nx,ny)); q.append((nx,ny))
        return seen
    reach_cells = reach(*w.spawn["安镇"])
    reach_places = [n for n,s in w.places.items() if s["cells"] & reach_cells]
    print(f"连通性: 从安镇老宅可达 {len(reach_places)}/{len(w.places)} 地点: {reach_places}")
    # 所有出生点连通性
    bad = [a for a,p in w.spawn.items() if not w.is_walkable(*p)]
    print("出生点不可通行:", bad if bad else "无")
    json.dump(w.to_json(), open("/home/ubuntu/atria_world.json","w"), ensure_ascii=False, indent=1)
    print("世界已存 /home/ubuntu/atria_world.json")
