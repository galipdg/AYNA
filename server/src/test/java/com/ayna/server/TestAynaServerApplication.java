package com.ayna.server;

import org.springframework.boot.SpringApplication;

public class TestAynaServerApplication {

	public static void main(String[] args) {
		SpringApplication.from(AynaServerApplication::main).with(TestcontainersConfiguration.class).run(args);
	}

}
