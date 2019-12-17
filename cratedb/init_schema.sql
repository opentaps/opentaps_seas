-- This file is part of opentaps Smart Energy Applications Suite (SEAS).

-- opentaps Smart Energy Applications Suite (SEAS) is free software:
-- you can redistribute it and/or modify
-- it under the terms of the GNU General Public License as published by
-- the Free Software Foundation, either version 3 of the License, or
-- (at your option) any later version.

-- opentaps Smart Energy Applications Suite (SEAS) is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU Lesser General Public License for more details.

-- You should have received a copy of the GNU Lesser General Public License
-- along with opentaps Smart Energy Applications Suite (SEAS).
-- If not, see <https://www.gnu.org/licenses/>.

-- Run this if Volttron did not init the Schema already
-- this can be used for example on test instances

CREATE ANALYZER "tree" (
   TOKENIZER tree
   WITH (
      type = 'path_hierarchy',
      delimiter = '/'
   ));

CREATE TABLE IF NOT EXISTS "volttron"."topic" (
   "kv_tags" OBJECT (DYNAMIC) AS (
      "dis" STRING,
      "id" STRING
   ),
   "m_tags" ARRAY(STRING),
   "topic" STRING,
   PRIMARY KEY ("topic")
) CLUSTERED INTO 4 SHARDS
WITH (
   "allocation.max_retries" = 5,
   "blocks.metadata" = false,
   "blocks.read" = false,
   "blocks.read_only" = false,
   "blocks.read_only_allow_delete" = false,
   "blocks.write" = false,
   column_policy = 'dynamic',
   "mapping.total_fields.limit" = 1000,
   max_ngram_diff = 1,
   max_shingle_diff = 3,
   number_of_replicas = '0-1',
   refresh_interval = 1000,
   "routing.allocation.enable" = 'all',
   "routing.allocation.total_shards_per_node" = -1,
   "translog.durability" = 'REQUEST',
   "translog.flush_threshold_size" = 536870912,
   "translog.sync_interval" = 5000,
   "unassigned.node_left.delayed_timeout" = 60000,
   "warmer.enabled" = true,
   "write.wait_for_active_shards" = 'ALL'
);

CREATE TABLE IF NOT EXISTS "volttron"."data" (
   "double_value" DOUBLE GENERATED ALWAYS AS TRY_CAST("string_value" AS double),
   "meta" OBJECT (DYNAMIC) AS (
      "type" STRING,
      "tz" STRING,
      "units" STRING
   ),
   "source" STRING,
   "string_value" STRING,
   "topic" STRING,
   "ts" TIMESTAMP,
   "week_generated" TIMESTAMP GENERATED ALWAYS AS date_trunc('week', "ts"),
   PRIMARY KEY ("topic", "ts", "week_generated"),
   INDEX "topic_ft" USING FULLTEXT ("topic") WITH (
      analyzer = 'standard'
   ),
   INDEX "taxonomy" USING FULLTEXT ("topic") WITH (
      analyzer = 'tree'
   )
)
CLUSTERED BY ("topic") INTO 6 SHARDS
PARTITIONED BY ("week_generated")
WITH (
   "allocation.max_retries" = 5,
   "blocks.metadata" = false,
   "blocks.read" = false,
   "blocks.read_only" = false,
   "blocks.read_only_allow_delete" = false,
   "blocks.write" = false,
   column_policy = 'dynamic',
   "mapping.total_fields.limit" = 1000,
   max_ngram_diff = 1,
   max_shingle_diff = 3,
   number_of_replicas = '0-1',
   refresh_interval = 1000,
   "routing.allocation.enable" = 'all',
   "routing.allocation.total_shards_per_node" = -1,
   "translog.durability" = 'REQUEST',
   "translog.flush_threshold_size" = 536870912,
   "translog.sync_interval" = 5000,
   "unassigned.node_left.delayed_timeout" = 60000,
   "warmer.enabled" = true,
   "write.wait_for_active_shards" = 'ALL'
);
