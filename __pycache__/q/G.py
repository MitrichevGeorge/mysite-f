

n, m = map(int, input().split())
edges = [tuple(map(int, input().split())) for _ in range(m)]
rez = "YES"
adjacency_matrix = [[False] * n for _ in range(n)]
    
for u, v in edges:
    adjacency_matrix[u - 1][v - 1] = True
    adjacency_matrix[v - 1][u - 1] = True

for u in range(n):
    for v in range(n):
        if adjacency_matrix[u][v]:
            for w in range(n):
                if adjacency_matrix[v][w]:
                    if not adjacency_matrix[u][w]:
                        rez = "NO"

print(rez)
