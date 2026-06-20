`timescale 1ns/1ps

module cryo_brain_decoder_visible_tb;
    logic clk;
    logic rst_n;
    logic syndromes_valid;
    logic [7:0] syndromes;
    logic corrections_valid;
    logic [3:0] corrections;
    logic [7:0] confidence;

    cryo_brain_decoder dut (
        .clk(clk),
        .rst_n(rst_n),
        .syndromes_valid(syndromes_valid),
        .syndromes(syndromes),
        .corrections_valid(corrections_valid),
        .corrections(corrections),
        .confidence(confidence)
    );

    initial clk = 0;
    always #5 clk = ~clk;

    task automatic drive_vector(
        input logic [7:0] vector_syndromes,
        output logic vector_valid,
        output logic [3:0] vector_corrections,
        output logic [7:0] vector_confidence
    );
        @(negedge clk);
        syndromes = vector_syndromes;
        syndromes_valid = 1'b1;
        @(posedge clk);
        #1;
        vector_valid = corrections_valid;
        vector_corrections = corrections;
        vector_confidence = confidence;
        @(negedge clk);
        syndromes_valid = 1'b0;
        @(posedge clk);
    endtask

    task automatic check_stim_benchmark;
        string vector_path;
        int fd;
        int rc;
        int vectors;
        int passes;
        int failures;
        int valid_count;
        longint confidence_sum;
        longint exact_ppm;
        longint confidence_ppm;
        logic [7:0] vector_syndromes;
        logic [3:0] expected;
        logic vector_valid;
        logic [3:0] vector_corrections;
        logic [7:0] vector_confidence;

        if (!$value$plusargs("BENCHMARK_VECTORS=%s", vector_path)) begin
            $display("SCENARIO stim_surface_code_benchmark FAIL");
            $display("BENCHMARK stim_surface_code vectors=0 passes=0 failures=0 valid=0 exact_ppm=0 confidence_ppm=0");
            $finish(1);
        end
        fd = $fopen(vector_path, "r");
        if (fd == 0) begin
            $display("SCENARIO stim_surface_code_benchmark FAIL");
            $display("BENCHMARK stim_surface_code vectors=0 passes=0 failures=0 valid=0 exact_ppm=0 confidence_ppm=0");
            $finish(1);
        end

        vectors = 0;
        passes = 0;
        failures = 0;
        valid_count = 0;
        confidence_sum = 0;
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%h %h\n", vector_syndromes, expected);
            if (rc == 2) begin
                drive_vector(vector_syndromes, vector_valid, vector_corrections, vector_confidence);
                vectors++;
                if (vector_valid) begin
                    valid_count++;
                    confidence_sum += int'(vector_confidence);
                end
                if (vector_valid && vector_corrections === expected) begin
                    passes++;
                end else begin
                    failures++;
                end
            end
        end
        $fclose(fd);

        exact_ppm = vectors == 0 ? 0 : (passes * 1000000) / vectors;
        confidence_ppm = vectors == 0 ? 0 : (confidence_sum * 1000000) / (vectors * 255);
        $display(
            "BENCHMARK stim_surface_code vectors=%0d passes=%0d failures=%0d valid=%0d exact_ppm=%0d confidence_ppm=%0d",
            vectors,
            passes,
            failures,
            valid_count,
            exact_ppm,
            confidence_ppm
        );
        if (vectors > 0 && valid_count == vectors) begin
            $display("SCENARIO stim_surface_code_benchmark PASS");
        end else begin
            $display("SCENARIO stim_surface_code_benchmark FAIL");
            $finish(1);
        end
    endtask

    initial begin
        rst_n = 0;
        syndromes_valid = 0;
        syndromes = 0;
        repeat (3) @(posedge clk);
        rst_n = 1;
        check_stim_benchmark();
        $finish(0);
    end
endmodule
