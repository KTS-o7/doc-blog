+++
title = 'Coin Piles'
date = 2025-09-23T14:38:08+05:30
draft = true
math = true
+++

Link to the problem : [Coin Piles](https://cses.fi/problemset/task/1754)

## Intuition
From the two piles we can perform the following operations:
- Remove 1 coin from pile `A` and 2 coins from pile `B`
OR
- Remove 2 coins from pile `A` and 1 coin from pile `B`

We need to check if we can make these operations to make both piles empty.

So thinking about it we can understand the following points
- Each time we are reducing the total count by 3.
- So if the total count is not divisible by 3, then it is not possible to make both piles empty.
- Another case is when one of the pile is substantially greater than the other, then it is not possible to make both piles empty.
- To find the limiting conditions we need to see like this

The count of coins in smaller piles shud be atleast be equal to half of the counts of coins in the larger pile.
This is the limiting condition because we can only remove 1 coin from pile `A` and 2 coins from pile `B` or 2 coins from pile `A` and 1 coin from pile `B`.
so mathematically it can be written as
if a<=b then we need to check if a >= b/2
because if  a < b/2 then a goes to 0 faster than b
  