# Title     : Simulations and interactions
# Objective : Simulation results and interactions insights
# Created by: Yuan Liao
# Created on: 2024-02-29

library(dplyr)
library(ggplot2)
library(Hmisc)
library(ggbeeswarm)
library(cowplot)
library(ggridges)
library(ggthemes)
library(ggpubr)
library(ggdensity)
library(arrow)
library(scales)
library(ggExtra)
library(hrbrthemes)
library(magick)

options(scipen=10000)

# ----- Simulation results -----
df.sims <- as.data.frame(read_parquet('results/plot/seg_sims_plot.parquet'))
df.plot <- df.sims
df.plot$variable <- factor(df.plot$variable,
                           levels=c('ice_enh', 'ice_e1', 'ice_e2'),
                           labels=c('Empirical', 'No-homophily', 'Equalized mobility\n & no-homophily'))
# df.plot$region <- factor(df.plot$region,
#                            levels=c('Stockholm', 'Gothenburg', 'Malmo'),
#                            labels=c('Stockholm', 'Gothenburg', 'Malmo'))
set.seed(68)
# df.plot <- rbind(rbind(sample_n(df.plot[df.plot$region == 'Stockholm',], 5000),
#                  sample_n(df.plot[df.plot$region == 'Gothenburg',], 5000)),
#                  sample_n(df.plot[df.plot$region == 'Malmo',], 5000))
df.plot <- sample_n(df.plot, 5000)

df.sims.stats <- df.sims %>%
  group_by(variable, grp_r) %>% # , region
  summarise(value_50 = wtd.quantile(value, weights=wt_p, probs = 0.5, na.rm = TRUE),
            value_25 = wtd.quantile(value, weights=wt_p, probs = 0.25, na.rm = TRUE),
            value_75 = wtd.quantile(value, weights=wt_p, probs = 0.75, na.rm = TRUE))
df.sims.stats$variable <- factor(df.sims.stats$variable,
                           levels=c('ice_enh', 'ice_e1', 'ice_e2'),
                           labels=c('Empirical', 'No-homophily', 'Equalized mobility\n & no-homophily'))

g1 <- ggplot(data = df.plot,
             aes(x = value, weight = wt_p, y = variable, color=grp_r)) +
  theme_hc() +
  geom_segment(aes(x = 0, y = 3.5, xend = 1, yend = 3.5),
                 arrow = arrow(type = "closed", length = unit(0.1, "inches")),
                 colour = "black", size=0.3) +
  geom_label(aes(x = 0.7, y = 3.4), label = "Native-born\n segregated", fill = "white",
               colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_segment(aes(x = 0, y = 3.5, xend = -1, yend = 3.5),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(aes(x = -0.7, y = 3.4), label = "Foreign-born\n segregated", fill = "white",
             colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_vline(aes(xintercept = 0), color='gray', size=0.6) +
  geom_point(aes(x=0, y=3.5), color='black', size=2) +
  scale_y_discrete() +
  geom_point(position = position_jitterdodge(jitter.width = 0.25, dodge.width = 0.7),
             size=0.06, alpha=0.1) +
  geom_errorbar(data = df.sims.stats, inherit.aes = FALSE,
                aes(xmin=value_25, xmax=value_75, y = variable, color = grp_r),
                width=0.3, size=0.5,
                position = position_dodge(.7)) +
  geom_point(data = df.sims.stats, inherit.aes = FALSE,
                aes(x=value_50, y = variable, color = grp_r),
                position = position_dodge(.7), size=1.3) +
#  facet_grid(.~region) +
  xlim(c(-1, 1)) +
  scale_fill_manual(name = 'Nativity group',
                    breaks = c('F', 'D'),
                    values = c('#601200', '#001260')) +
  scale_color_manual(name = 'Nativity group', breaks = c('F', 'D'), values = c('#601200', '#001260')) +
  labs(x = "Nativity segregation outside residential area", y = "") +
  theme(strip.background = element_blank(), legend.position = 'top')

ggsave(filename = "figures/panels/fig2_b.png", plot=g1,
       width = 7, height = 3.5, unit = "in", dpi = 300, bg = 'white')

# --- Group interactions ----
df.inter <- as.data.frame(read_parquet('results/plot/group_interactions_plot_combined.parquet'))
df.inter.stats <- df.inter %>%
  group_by(inter_type, Group, Source) %>%
  summarise(value_50 = wtd.quantile(value, weights=wt_p, probs = 0.5, na.rm = TRUE),
            value_25 = wtd.quantile(value, weights=wt_p, probs = 0.25, na.rm = TRUE),
            value_75 = wtd.quantile(value, weights=wt_p, probs = 0.75, na.rm = TRUE))

inter_type.labs <- c(sprintf('D \u2192 D'), sprintf('N \u2192 N'), sprintf('F \u2192 F'),
                     sprintf('D \u2192 F'), sprintf('F \u2192 D'),
                     sprintf('N \u2192 D'), sprintf('D \u2192 N'), sprintf('F \u2192 N'), sprintf('N \u2192 F'))
df.inter.stats$inter_type <- factor(df.inter.stats$inter_type,
                           levels=c('DD', 'NN', 'FF',
                                    'DF', 'FD',
                                    'ND', 'DN', 'FN', 'NF'),
                           labels=inter_type.labs)
df.inter.stats$Group <- factor(df.inter.stats$Group,
                               levels=c(1, 2, 3),
                               labels=c('Within group', 'Between foreign-born and native-born',
                                    'Others with mixed group'))
df.inter.stats$Source <- factor(df.inter.stats$Source,
                               levels=c('Empirical', 'No-homophily', 'Equalized mobility & no-homophily'),
                               labels=c('Empirical', 'No-homophily', 'Equalized mobility\n & no-homophily'))

g2 <- ggplot(data = df.inter.stats,
             aes(y=Source, color=inter_type)) +
  theme_hc() +
  geom_vline(aes(xintercept = 0), color='gray', size=0.3, show.legend = F) +
  geom_errorbar(aes(xmin=value_25, xmax=value_75),
                width=0.3, size=0.5,
                position = position_dodge(.7), show.legend = F) +
  geom_point(aes(x=value_50), position = position_dodge(.7), size=1.3, show.legend = F) +
  geom_text(aes(x=value_50, label=inter_type), position = position_dodge(.7),
            hjust=0.5, vjust=-1, show.legend = F, size=3) +
  facet_grid(.~Group) +
  scale_color_manual(breaks = inter_type.labs,
                     values = c('#001260', 'gray45', '#601200',
                                 '#4D1213', '#13124D',
                                '#666A7A', '#1A2866', '#66281A', '#7A6A66')) +
  labs(x = "Deviation from baseline exposure (%)", y = "") +
  theme(strip.background = element_blank())

G <- ggarrange(g1, g2, ncol = 1, nrow = 2, labels = c('a', 'b'), heights = c(1, 1.5))
ggsave(filename = "figures/panels/seg_disp_fig2.png", plot=G,
       width = 10, height = 7, unit = "in", dpi = 300, bg = 'white')

# --- Cleaner version of interactions ---
df.inter.stats <- df.inter.stats %>%
  filter((inter_type != sprintf('N \u2192 D')) & (inter_type != sprintf('N \u2192 F')))

g3 <- ggplot(data = df.inter.stats,
             aes(y=Source, color=inter_type)) +
  theme_hc() +
  geom_vline(aes(xintercept = 0), color='gray', size=0.3, show.legend = F) +
  geom_errorbar(aes(xmin=value_25, xmax=value_75),
                width=0.3, size=0.5,
                position = position_dodge(.7), show.legend = F) +
  geom_point(aes(x=value_50), position = position_dodge(.7), size=1.3, show.legend = F) +
  geom_text(aes(x=value_50, label=inter_type), position = position_dodge(.7),
            hjust=0.5, vjust=-1, show.legend = F, size=3) +
  facet_grid(.~Group) +
  scale_color_manual(breaks = inter_type.labs,
                     values = c('#001260', 'gray45', '#601200',
                                 '#13124D', '#4D1213',
                                '#666A7A', '#1A2866', '#66281A', '#7A6A66')) +
  labs(x = "Deviation from baseline exposure (%)", y = "") +
  theme(strip.background = element_blank())


ggsave(filename = "figures/panels/fig2_d.png", plot=g3,
       width = 9, height = 4, unit = "in", dpi = 300, bg = 'white')

# G <- ggarrange(g1, g3, ncol = 1, nrow = 2, labels = c('a', 'b'), heights = c(1, 1.5))
# ggsave(filename = "figures/panels/seg_disp_fig2_r.png", plot=G,
#        width = 10, height = 7, unit = "in", dpi = 300, bg = 'white')

# ----- Combine labeled images -------
# Load the two input .png images
read.img <- function(path, lb){
  image <- image_read(path) %>%
    image_annotate(lb, gravity = "northwest", color = "black", size = 70, weight = 700)
  return(image)
}
image1 <- read.img(path="figures/panels/simulation_diagram.png", lb='a')
image2 <- read.img(path="figures/panels/fig2_b.png", lb='b')
image4 <- read.img(path="figures/panels/fig2_d.png", lb='d')


## Combine images 2-4
# Get width of image 2
image2_height <- image_info(image2)$height

# Create blank space between them and stack three
blank_space_h1 <- image_blank(2, image2_height, color = "white")
combined_image1 <- image_append(c(image1, blank_space_h1, image2), stack = F)
combined_image1_width <- image_info(combined_image1)$width

## Combine image1 with combined_image1
# Get height of image 1
image4_height <- image_info(image4)$height
image3_resized <- image_resize(image_read("figures/panels/group_interaction_diagram.png"),
                               paste0("x", image4_height)) %>%
    image_annotate('c', gravity = "northwest", color = "black", size = 70, weight = 700)

# Create a blank space image
blank_space_h2 <- image_blank(2, image4_height, color = "white")
combined_image2 <- image_append(c(image3_resized, blank_space_h2, image4), stack = F)

# Combine the images side by side
blank_space_w <- image_blank(combined_image1_width, 1, color = "white")
combined_image <- image_append(c(combined_image1, blank_space_w, combined_image2), stack = T)
image_write(combined_image, "figures/panels/seg_disp_fig2.png")

