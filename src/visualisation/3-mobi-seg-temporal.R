# Title     : Temporal patterns of mobility-related segregation in contrast with housing segregation
# Objective : Time series
# Created by: Yuan Liao
# Created on: 2023-1-31

library(dplyr)
library(ggplot2)
library(ggpubr)
options(scipen=10000)

df <- read.csv('results/mobi_seg_tempo.csv')

g1 <- ggplot(data=df[df$deso_3 == 1,]) +
  geom_line(aes(x=time_seq/2, y=evenness_income, group=type, color=type)) +
  facet_wrap(holiday~weekday, labeller = label_both, ncol=4) +
  theme_minimal() +
  labs(x = 'Time (h)', y = 'Unevenness of income')

g2 <- ggplot(data=df[df$deso_3 == 14,]) +
  geom_line(aes(x=time_seq/2, y=evenness_income, group=type, color=type)) +
  facet_wrap(holiday~weekday, labeller = label_both, ncol=4) +
  theme_minimal() +
  labs(x = 'Time (h)', y = 'Unevenness of income')

g3 <- ggplot(data=df[df$deso_3 == 12,]) +
  geom_line(aes(x=time_seq/2, y=evenness_income, group=type, color=type)) +
  facet_wrap(holiday~weekday, labeller = label_both, ncol=4) +
  theme_minimal() +
  labs(x = 'Time (h)', y = 'Unevenness of income')

G <- ggarrange(g1, g2, g3, ncol = 1, nrow = 3, common.legend = T,
               labels = c('Stockholm', 'Gothenburg', 'Malmo'))
ggsave(filename = paste0("figures/mobi_seg_tempo.png"), plot=G,
       width = 8, height = 10, unit = "in", dpi = 300)