-- 按部门分组，每组内按工资排名
SELECT name, department, salary,
       ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) as rank
FROM employees;

-- 结果：
-- 张三 | 技术部 | 20000 | 1
-- 李四 | 技术部 | 18000 | 2
-- 王五 | 市场部 | 15000 | 1
-- 赵六 | 市场部 | 12000 | 2

-- 只要每个部门第一名：
SELECT name, department, salary
FROM (
    SELECT name, department, salary,
           ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) as rank
    FROM employees
) t
WHERE rank = 1;
